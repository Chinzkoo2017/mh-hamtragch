# Хоолойн файлууд

**Хялбар арга:** ElevenLabs дээр reel-ийн бүх мөрийг (Add speaker) нэг дор үүсгээд `assets/voice/<reel>.mp3` нэрээр хадгална
(promo, ashitaba, cardio, squalen, iodium, artro, collagen, toothpaste). Build нь мөр хоорондын завсар, хоолойны өндөр намаар
нь мөр тус бүрээр (`<reel>/01.mp3 …`) автоматаар хэсэглээд, reel-ийн аятай нийлүүлж `assets/music/<reel>.mp3` үүсгэнэ.

Мөрийн дараалал нь `data/reels.json`-ийн beats-тэй яг ижил байх ёстой (`data/reel-voice-script.md`).
Хүсвэл мөр бүрийг шууд `<reel>/01.mp3, 02.mp3 …` гэж хийж болно.
