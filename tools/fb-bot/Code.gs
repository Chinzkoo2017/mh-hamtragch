/**
 * Эрүүл амьдралын хөтөч — Facebook коммент бот (Google Apps Script webhook)
 *
 * Хийх зүйл: хуудасны пост/рилс дээр «Cardio» гэх мэт түлхүүр үгтэй коммент бичигдэхэд
 *   1) комментын дор олон нийтэд харагдах талархлын хариу бичнэ;
 *   2) коммент бичсэн хүнд Messenger-ээр (Private Reply) PDF холбоос илгээнэ.
 *
 * Тохиргоо (Project Settings → Script properties) — ТОКЕНЫГ ЗӨВХӨН ТА ӨӨРӨӨ ОРУУЛНА:
 *   PAGE_TOKEN    — Page access token (pages_messaging, pages_manage_engagement,
 *                   pages_read_engagement, pages_manage_metadata эрхтэй)
 *   VERIFY_TOKEN  — webhook баталгаажуулах дурын нууц үг (Meta дээр ижлийг бичнэ)
 *   PAGE_ID       — 869620286389880
 */

const GRAPH = 'https://graph.facebook.com/v25.0';

// Түлхүүр үг → илгээх холбоос. Шинэ бүтээгдэхүүн нэмэхдээ энд мөр нэмнэ.
const KEYWORDS = [
  { re: /(cardio|кардио)/i, name: 'Cardio Marine', url: 'https://eruul-amidral.com/cardio.pdf' },
];

const PUBLIC_REPLY = 'Баярлалаа 🙏 Танд чатаар илгээлээ.';
const privateText = k =>
  `Сайн байна уу 😊 ${k.name}-ийн танилцуулгыг илгээж байна: ${k.url}\n` +
  'Асуух зүйл байвал энд бичээрэй, бид хариулъя.';

function props_() { return PropertiesService.getScriptProperties(); }

// Webhook баталгаажуулалт (Meta GET хүсэлт)
function doGet(e) {
  const p = e && e.parameter || {};
  if (p['hub.mode'] === 'subscribe' && p['hub.verify_token'] === props_().getProperty('VERIFY_TOKEN')) {
    return ContentService.createTextOutput(p['hub.challenge']);
  }
  return ContentService.createTextOutput('ok');
}

// Webhook үйл явдал (Meta POST хүсэлт)
function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    (body.entry || []).forEach(entry => (entry.changes || []).forEach(handleChange_));
  } catch (err) {
    console.error(err);
  }
  return ContentService.createTextOutput('EVENT_RECEIVED');
}

function handleChange_(ch) {
  const v = ch.value || {};
  if (ch.field !== 'feed' || v.item !== 'comment' || v.verb !== 'add') return;
  const pageId = props_().getProperty('PAGE_ID');
  if (!v.comment_id || (v.from && v.from.id === pageId)) return;      // өөрийн хуудасны коммент биш
  const k = KEYWORDS.find(x => x.re.test(v.message || ''));
  if (!k) return;

  // Давхар хариулахаас сэргийлэх
  const lock = LockService.getScriptLock(); lock.waitLock(10000);
  try {
    const key = 'done_' + v.comment_id;
    if (props_().getProperty(key)) return;
    // Комментыг Graph API-гаар дахин шалгана (хуурамч хүсэлтээс хамгаална)
    const c = graph_('GET', `/${v.comment_id}?fields=message,from`);
    if (!c || !k.re.test(c.message || '') || (c.from && c.from.id === pageId)) return;
    props_().setProperty(key, new Date().toISOString());
  } finally { lock.releaseLock(); }

  graph_('POST', `/${pageId}/messages`, {
    recipient: { comment_id: v.comment_id },
    message: { text: privateText(k) },
    messaging_type: 'RESPONSE',
  });
  graph_('POST', `/${v.comment_id}/comments`, { message: PUBLIC_REPLY });
}

function graph_(method, path, payload) {
  const token = props_().getProperty('PAGE_TOKEN');
  const url = GRAPH + path + (path.includes('?') ? '&' : '?') + 'access_token=' + encodeURIComponent(token);
  const opt = { method: method.toLowerCase(), muteHttpExceptions: true, contentType: 'application/json' };
  if (payload) opt.payload = JSON.stringify(payload);
  const r = UrlFetchApp.fetch(url, opt);
  if (r.getResponseCode() >= 300) { console.error(path, r.getResponseCode(), r.getContentText()); return null; }
  return JSON.parse(r.getContentText() || '{}');
}

// Гараар туршихад: хуудсыг webhook-д бүртгэх (токен оруулсны дараа нэг удаа ажиллуулна)
function subscribePage() {
  const pageId = props_().getProperty('PAGE_ID');
  console.log(graph_('POST', `/${pageId}/subscribed_apps?subscribed_fields=feed`));
}
