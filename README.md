# Эрүүл амьдралын хөтөч — Marine Health бизнес хамтрагч

Сайт: https://chinzkoo2017.github.io/mh-hamtragch/

Marine Health бүтээгдэхүүний танилцуулга, 11-р сарын урамшуулал, reel видео, гэрчилгээ.
Сайт дээр худалдан авалт хийгдэхгүй. «Захиалах» товч бүхэн албан ёсны дэлгүүр рүү лавлах холбоосоор шилжүүлнэ.

## Бүтэц
- `index.html` — сайт (бүтээгдэхүүний дэлгэрэнгүй, багц, reel тоглуулагч, гэрчилгээ)
- `data/reels.json` — reel скрипт (дуу хоолойгоор уншигдах текст `say`, дэлгэцийн том бичиг `cap`, зураг `img`)
- `data/assets.json` — татах зураг, гэрчилгээний жагсаалт
- `tools/build.py` + `.github/workflows/build-assets.yml` — `data/` өөрчлөгдөхөд GitHub Actions зураг, гэрчилгээ татаж, монгол дуу хоолой (mn-MN-YesuiNeural) үүсгээд `assets/` руу хадгална

## Шууд холбоос (Messenger, пост-д)
- Бүтээгдэхүүн: `#ashitaba`, `#cardio`, `#squalen`, `#iodium`, `#artro`, `#collagen`, `#toothpaste`
- Багц: `#b2301` … `#b2306`, `#b2279`, `#b2275`, `#b2127`, `#b2102`
- Reel: `#reel-promo`, `#reel-ashitaba`, `#reel-cardio`, …

## Засах
- Reel-ийн текстийг `data/reels.json`-д засаад push хийхэд дуу хоолой автоматаар шинэчлэгдэнэ.
- Үнэ, урамшуулал: `index.html` доторх `P`, `DEALS`, `GIFTS`, `SETS`, `SALE_END`.

Энэ нь Marine Health-ийн албан ёсны вэб сайт биш. Бүтээгдэхүүний зураг, гэрчилгээ: Marine Health.
