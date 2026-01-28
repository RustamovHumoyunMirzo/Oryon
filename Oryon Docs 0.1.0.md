# Oryon Documentation

## Kirish
Oryon bu interpreterga asoslangan dasturlash tili hisoblanadi. Unda ja'mi 40 ta kalit so'zlar mavjud. Ushbu til juda yengil, hajmi ~8MB atrofida va avtomatik xotira menejmentiga ega. Boshqa tillar kabi bu ham avtonom, ya'ni, sizdan boshqa hech qanday fayl, qo'shimcha dasturlarni o'rnatishni talab qilmaydi. Shunchaki installerni o'zini yuklaysiz va o'rnatasiz. Hozirda Oryon faqat Windows operatsion tizimini qo'llab quvvatlaydi.

**O'rnatish & Sozlash**

`Oryon Setup` faylini yuklab bo'lganingizdan so'ng unga ikki marta bosib oching

 1. Tilni tanlang
 2. Shartlarga rozilik bildiring
 3. O'rnatish tugmasini bosing

Odatda dastur `C:\Program Files\Oryon\` manziliga saqlanadi
Ishga tushirish uchun Oryon o'rnatilgan manzilda joylashgan executable faylni toping `oryon.exe`.
Topgan dasturingiz ustiga ikki marta bosing va Oryonning REPL muhiti ochiladi, `h` yoki `help` buyrug'i bilan batafsil o'rganishingiz mumkin. Hozirda bizga ishga tushirish kerak va boshqasi qiziq emas, buning uchun ushbu buyruq sizga hizmat qiladi: `run <oryon fayl manzili>`. Aytgancha, oryon fayl kengaytmasi quyidagilar, `.or` va `.oryon`.

**Birinchi dastur**

Kompyuter xotirasidan har qanday joyga oryon faylini yarating va ikki marta bosing. Bu jarayon to'g'ridan-to'g'ri terminalda ochiladi, agar yozgan dasturingiz o'z ichiga loopni qabul qilmasa, terminal oynasi faqat soniyalar davomida faol bo'ladi, bu bug hisoblanmaydi, sababi dasturni loopdan ajratish uchun hizmat qiladi.
Shunday ekan, birinchi dastur sifatida buni faylga kiriting:

    output("Salom Dunyo!")
    
Bu esa, buyruqlar qatorida *Salom Dunyo!* natijasini chiqaradi. Agar buni siz ham ko'rgan bo'lsangiz, tabriklaymiz, siz hozirgina o'z dasturingizni yozdingiz.

## Til Asoslar

**Sintaksis**

Oryon o'rganish uchun oson til hisoblanadi va tushunarli sintaksisga ega. Koddagi har bir ishora token hisoblanadi va ular joylashuvi va tartibiga ko'ra farqlanadi. Kichik bir imloviy xato ham dasturni ishdan chiqarishi mumkin. Keling, lexer moduli tushunadigan kalit so'zlarni yoxud asosiy tokenlarni o'rganamiz.

 - `->` ARROW — Statement (bayonot) boshlanishida qo'llaniladi
 - `end` END — Statement tugashida qo'llaniladi
 - `(` LPAREN — Chap qavs, metodlar va ba'zi bayonotlarning argument qabul qiluvchi qismini boshlab beradi
 - `)` RPAREN — O'ng qavs, metodlar va ba'zi bayonotlarning argument qabul qiluvchi qismini tugatib beradi
 - `.` DOT — Nuqta, asosan obyektlarning mulklariga ega chiqishda qo'llaniladi
 - `{}[]` LRBRACE va LRBRACKET — Qavs turlari, ro'yxatlar va massivlarni boshlash va tugatishda qo'llaniladi
 - `\n` NEWLINE — Yangi bo'sh qator, tokenlarni ajratishda qo'llaniladi
 - `:` COLON — Ikki nuqta
 - `,` COMMA — Vergul

Bundan tashqari tilda `ID`, `SKIP`, `MISMATCH`, `OP` tokenlari ham mavjud.
Misol uchun:

    func foo(arg) -> void
		  output(arg++)
    end
 
Bu yerda func, foo, arg, void va output so'zlari `ID` hisoblanadi. ++ `OP` va qavslar ham bor `LRPAREN`.
`OP` sarasiga kiruvchi tokenlar (Operatorlar):

 - ===, ||, &&, >, <
 - ==, !=, <=, >=
 - +=, -=, *=, /=, %=
 - **, //, ++, \-\-
 - <<, >>
 - +, -, *, /, %, !, #, =, ^, &

Izoh tizimi C dasturlash tili kabi, `// Yakka qator izohi` va `/* Bir nechta qatorli izoh */`.

**O'zgaruvchilar**

Oryon tilida o'zgaruvchilar static hisoblanib, faqatgina o'zinging boshlang'ich turiga hos bo'lgan qiymatni qabul qiladi. Qo'shimcha xavfsizlik uchun bularga istisno bo'luvchi elementlar ham mavjud. Bular: `auto` va `any`. auto bu o'zgaruvchilarga nisbatan qo'llaniladi va dynamic usulni ishlatadi, ya'ni auto turdagi o'zgaruvchi o'zida avval son, keyinchalik satrni ham ushlab tura oladi. any esa funksiyalarning qiymat qaytarish turi noma'lum bo'lganda qo'l keladi.
O'zgaruvchi turlari:

 - int — butun son `123`
 - long — ko'proq sonlarni qamrab oluvchi butun son `123`
 - float — real son `12.3`
 - double — yuqori aniqlikdagi real son `12.3`
 - str — satr `"Salom Dunyo!"`
 - bool — mantiq `true`/`false`
 - list — ro'yxat `[0,1,2,3]`
 - map — massiv `{"ism": "Falonchi"}`
 - tuple — to'plam `(0,1,2,3)`
 - null —bo'sh qiymat

Misol uchun:

    int son = 0 // o'zgaruvchini e'lon qilish
    son = 1 // o'zgaruvchi qiymatini qayta yozish
 
To'plam o'zgaruvchilari bir-birlarini ichiga qiymat sifatida qabul qila oladilar, `list r = [0,1,(2,3),4]`. `tuple` turi immutable hisoblanib hech qanday metodalarga ega emas va o'zgarmaydi, faqatgina o'qish mumkin holos.

    list l = ["salom", "dunyo"]
    output(l[0]) // ro'yxatdan indeks orqali ma'lumot olish, birinchi element doimo 0 indeksga ega.
    // natija: salom
    
    l[1] = "salom dunyo" // ro'yxatning ichki elementini o'zgartirish
    
Massivlar tartibsiz deb aytiladi, aslida ular juda tartibli, sababi ularda indeks o'rniga kalitlar mavjud, `{"kalit": "qiymat"}`. Ulardan foydalanish ro'yxatga qaraganda farqli:

    map info = {"ism": "Men", "yosh": 99, "sudlangan": false}
    output(info.yosh) // mulkni kalit orqali olish, natija: 99
    info.ism = "Sen" // mulkni o'zgartirish
    output(info.sen) // natija: sen

`null` turi to'g'ridan-to'g'ri o'zgaruvchiga qo'llanilmaydi, aniqroq qilib aytganda faqat qiymat sifatida ishlatiladi. Faraz qiling, siz qabul qiladigan ma'lumot noma'lum. Bunday holatda uni null qiymatiga o'zgartiramiz va o'zgaruvchi qiymatsiz deb topiladi. Keyinchalik esa bu sizga halaqit bermaydi.

## Boshqaruv tuzilmalari

**Shart operatorlari**

Bunday operatorlar mantiqqa asoslangan holda oqimni boshqarishga yordam beradi. Bularga, `if`/`else`, looplar va boshqa operatorlar kiradi. `if`/`else`/`elseif` operatorlari agar, aks holda, va aks holda, agar deb tarjima qilinadi.

    if(1==1) ->
	    output("1 soni 1ga teng!")
	  elseif(1==0) ->
		  output("1 soni 0ga teng!")
	  else ->
		  output("1 soni 1ga teng emas!")
    end
    
Avval `if` qismi tekshiriladi, agar `true` rost qaytarsa (1==1) ichkariga o'tadi, aks holda `else`ning tana qismiga kiradi. Biz `elseif` operatorini ham ishlatishimiz mumkin, bu bizga `if` operatori yolg'on bo'lganda boshqa bir shartni tekshirishga imkon beradi va bu `else`dan avval ishga tushadi.

Boshqa bir operator `switch` ham mavjud, u bir vaqtning o'zida ko'plab qiymatlarni tenglik uchun tekshiradi.

    switch(20) ->
	    case 99:
	        output("Son 99 edi!")
	        break
	    case 10:
	        output("Son 10 edi!")
	        break
	    def:
	        output("Hech qaysi emas!")
	        break
	end

`def` identifikatori muqobil qiymat topilmaganda ishga tushadi, `case` esa variant. `switch` bayonoti tsikl hisoblanadi.

**Takrorlash operatorlari**

Oryon dasturlash tilida ikki xil loop operatori mavjud `for`, `while`. for operatori biror bir ro'yxatning har bir elementi uchun takror ishga tushadi. while esa kiritilgan shart yolg'on bo'lmagunga qadar.

    list l = [0,1,2,3]
    for(el in l) ->
	    output(el) // l ro'yxatining barcha elementlarini chiqaradi
    end
    
    while(1==1) ->
	    output("Salom Dunyo!") // ushbu loop cheksiz davom etadi, chunki 1 har doim 1ga teng va rost qiymat qaytaradi
    end

**Boshqaruv operatorlari**

Bularga `break`, `continue`, `return` kiradi. break tsikldan chiqarish uchun, continue tsiklni boshidan boshlash uchun, return qiymat qaytarish uchun ishlatiladi. Bo'sh return har doim `null` qaytaradi. Nafaqat loop ichida balki har qanday joyda return turgan joydan pastki qismini o'tkazib yuboradi. Lekin biz returnni bayonotdan tashqarida ishlata olmaymiz.

    while(1==1) ->
	    output("Salom!") // natija faqat bir marta chiqariladi, chunki break ishlatilmoqda va u tsiklni eng birinchi aylanishdayoq buzadi
	    break
    end
    
    while(true) ->
	    continue
	    output("Salom!") // natija hech qachon chiqmaydi, chunki continue tsiklni chiqarishgacha qayta boshlaydi va tsikl hech qachon u yerga yetib bormaydi
    end

## Modullar

Modullar nafaqat Oryon dasturlash tilida, balki umuman olganda, dasturlashda juda muhim ahamiyatga ega. Chunki biz yozayotgan dastur bir nechta fayllardan tashkil topishi uning tartibli, o'qilishi oson va kengaytiriladigan bo'lishini ta'minlaydi. Katta loyihalarda barcha kodni bitta faylga yozish nafaqat noqulay, balki xatolarga ham olib keladi.

Tashqi modullar nima?
Tashqi modullar — bu asosiy dastur faylidan tashqarida joylashgan va alohida fayllarda yozilgan kod bo‘laklaridir. Ular odatda ma’lum bir vazifani bajarishga mo‘ljallangan bo‘ladi va kerak bo‘lganda asosiy dasturga ulanadi (import qilinadi).

Tashqi modullar orqali:
-   kodni qayta ishlatish (reuse) mumkin bo‘ladi;
    
-   dastur tuzilmasi aniq va tushunarli bo‘ladi;
    
-   xatolarni topish va tuzatish osonlashadi;
    
-   jamoa bilan ishlash ancha qulaylashadi.

Ularni biz shunday qilib kod faylimizda ishlatamiz:

    import <mymodule>
va manabunday ham:

    import <mymodule> <qoshish>
Hozirda bizda ikki xil modul turi mavjud, tashqi va ichki. Tashqi modul biz yuqorida aytib o'tganimizdir. Ichki modul esa tilning o'zidagilari hisoblanadi va ko'pincha standart modul deb ataladi. Misol uchun `#math` moduli. Ichki modullarni, modul nomi kiritiladigan joyga `#` prefiksini qo'shish orqali qabul qilamiz:

    import <#math>
Import bayonotida biz ikkita parametrli maydon tuza olamiz, `import <birinchi> <ikkinchi>`. Ikkinchi maydon ixtiyoriy. Birinchisida modulni o'zi kiritilsa, ikkinchisida esa uning ichki obyektlari nazarda tutiladi, `import <#math> <Vector3>`. Matematika modulidan vektorni qabul qildik. Agar biz modulni o'zini import qilsak, keyinchalik uni nomi bilan ichki obyektlarini chaqiramiz, chunki modul butun holatida qabul qilindi va butun holatida ishlatiladi:

    import <#math>
    math.Vector3 vektor = math.Vector3(1,2,3)
Agarda aynan biror bir obyektni import qilsak, modul nomi kerak bo'lmaydi, chunki biz allaqachon obyektlarni ajratib oldik:

    import <#math> <Vector2, sqrt>
    Vector2 v = Vector2(sqrt(1), sqrt(2))
 Endi, bir savol tug'iladi, qanday qilib modulning barcha obyektlarini import qilib va shu bilan birgalikda modul nomini kiritmaslik mumkin? Ushbu prefiks `*` modulning barcha obyektlarini qabul qiladi lekin modulni o'zini emas.
 
    import <#math> <*>
    Vector3 v = Vector3(1,2,3)
Tashqi moduldan foydalanishda uning joylashuvi muhim ahamiyatga ega. Oryon tilida bu jarayon juda oson va qulay tashkil etilgan.

-   Agar tashqi modul va asosiy (bosh) modul bir xil papkada joylashgan bo‘lsa, import qilish uchun shunchaki modul nomini yozamiz:
    
    `import <modul>` 
    
-   Agar tashqi modul ichki kataloglardan birida joylashgan bo‘lsa, uni bosh modul turgan joydan boshlab nisbiy yo‘l orqali import qilamiz. Bunda yo‘l boshida `./` prefiksi modulning hozirgi joylashgan katalogini bildiradi:
    
    `import <./papka/modul>` 
    
    Bu yerda `./` — modulni qayerdan import qilayotganingiz (ya’ni, asosiy modul joylashgan papka) belgisi hisoblanadi.
    
-   Shu tariqa, modulning joylashuvi qanchalik chuqur bo‘lmasin, uning to‘liq nisbiy manzilini ko‘rsatib import qilish mumkin. Masalan:
    
    `import <./papka/ichki_papka/modul>` 

Qisqacha eslatma:
|Import sintaksisi| Joylashuv ma’nosi |
|--|--|
| `import <modul>` | Joriy (asosiy) modul bilan bir xil papkadan |
| `import <./papka/modul>` | Joriy papkadan `papka` ichidagi modul |
| `import <../modul>` | Bir daraja yuqoridagi papkadan modul |

Siklik import (circular import) nima?
Bu ikki yoki undan ortiq modul bir-birini o‘z ichiga qayta-qayta import qilishi holatidir. Boshqacha qilib aytganda, modul A modul B ni import qiladi, modul B esa yana modul A ni import qiladi — natijada import jarayoni doimiy aylanishga tushadi.

Nega siklik import muammo?

-   Siklik import dastur bajarilishida cheksiz aylanishga olib keladi.
    
-   Bu kodning to‘g‘ri ishlashini to‘xtatishi yoki xatolarga sabab bo‘lishi mumkin.
    
-   Modul hali to‘liq yuklanmasidan uning obyektlariga murojaat qilishga urinish xatolarga olib keladi.
    
-   Shu bois import jarayonida siklik bog‘lanishlar aniqlansa, tizim uni xato (exception) sifatida ko‘rsatadi va importni to‘xtatadi.

## Funksiyalar

**Funksiya tushunchasi**

Funksiya deganda matematikada `X`ning `Y`ga bogʻliqligi tushuniladi. Lekin dasturlashda ozgina farqli boʻlib, dasturning qayta ishlatib boʼladigan va maʼlum bir vazifani bajaradigan boʻlagi funksiya hisoblanadi.

Oryon dasturlash tilida funksiyadan ushbu koʻrinishda foydalanish mumkin:

    func ayirma(X, Y) -> void
        output("Natija:", X - Y)
    end
    
    ayirma(15, 10)

Ushbu dastur `X` qiymatdan `Y`ni ayirib, natijani buyruqlar qatoriga chiqaradi. Bu yerda `void` soʻzi funksiyaning turi, yaʼni zanjir. Funksiyalar `func` soʻzi bilan boshlanadi va `end` bilan tugaydi. Ularning orasida esa bajariladigan amallar kiritiladi. Oryon bayonotni boʻsh qoldirilishiga ruxsat beradi. Shu bilan birgalikda funksiya turini belgilanishini qatʼiy talab qiladi. Tur — bu funksiya qaytarishi majbur boʻlgan qiymatning turi. Funksiya turlariga barcha oʻzgaruvchi turlari kiradi (int, str, bool, map va h.k) va ikkita maxsus turlar, `void` va `any`. void — bu biz yuqorida koʻrganday zanjir deyiladi, yaʼni funksiya hech qanday qiymat qaytarmaydi. any — bu har qanday turni qaytaruvchi boʻlib, qaytariluvchi qiymat nomaʼlum boʻlgan paytlarda foyda beradi.

**Parametrlar va qaytarish qiymatlari**

Funksiya parametrlar orqali tashqi tomondan qiymatlar qabul qiladi va belgilangan turga mos ravishda qiymat qaytaradi (yoki `void` bo‘lsa, umuman qaytarmaydi).

Parametrlar funksiya nomidan keyin qavs ichida yoziladi va vergul bilan ajratiladi. Har bir parametr funksiya ichida o‘zgaruvchi sifatida ishlatiladi. Misol:

    func yigindi(A, B) -> int
        return A + B
    end

Bu yerda:
* A va B — parametrlar
* funksiya int turidagi qiymat qaytaradi

Funksiyani chaqirish:

    natija = yigindi(5, 7)
    output(natija)

Agar funksiya turi `void` bo‘lmasa, u albatta `return` operatori orqali qiymat qaytarishi shart. Oddiy holatda funksiyalar statik deb hisoblanadi. Misol uchun funksiya turi `int` (butun son) bo'lsa va u `str` (satr) qaytarsa, bu jarayon xatolik bilan tugaydi. Oryon dinamik funksiyalarni ham taklif etadi. Yuqorida aytilgandek `any` turi funksiyani har qanday qiymat qaytarishga undaydi.

**Rekursiya**

Rekursiya — bu funksiya o‘zini o‘zi chaqiradigan dasturlash usuli. Bu usul murakkab masalani kichikroq, o‘xshash masalalarga bo‘lib yechishga yordam beradi.

Faktorial matematikada quyidagicha aniqlanadi:

    n! = n × (n - 1)!
    1! = 1
Quyidagi misolda `factorial` funksiyasi rekursiya yordamida yozilgan:

    func factorial(n) -> int
        if (n == 1) ->
            return 1
        else ->
            return n * factorial(n - 1)
        end
    end
    
    output(factorial(5))
Qanday ishlaydi?

`factorial(5)` chaqirilganda:

    → 5 * factorial(4)
    → 4 * factorial(3)
    → 3 * factorial(2)
    → 2 * factorial(1)
    → 1
    
Natijalar ketma-ket qaytariladi va yakuniy javob olinadi.

## Obyektga yo‘naltirilgan dasturlash (OOP)

Obyektga yo‘naltirilgan dasturlash — bu dasturlash paradigmasi bo‘lib, unda dastur klasslar (sinflar) va obyektlar asosida quriladi. OOP kodni tuzilmali, tushunarli va qayta foydalanishga qulay qiladi.

**Klass va obyektlar**

Klass — bu obyektlar uchun shablon (model).
Obyekt — klass asosida yaratilgan real nusxa.
Klass e’lon qilish:

    class Mashina ->
        init(marka, tezlik, rang) ->
            this.brand = marka
            this.speed = tezlik
            this.colour = rang
        end
    
        func info() -> list
            return [this.brand, this.speed, this.colour]
        end
    end

Bu yerda:

-   `Mashina` — klass nomi
-   `init` — konstruktor
-   `this` — joriy obyektga ishora qiladi
-   `info()` — obyekt haqidagi ma’lumotni qaytaruvchi metod

Obyekt yaratish:

    Mashina car = Mashina("Gentra", 180, "Qora")
    output(car.info())

**Konstruktor**

Konstruktor (`init`) — obyekt yaratilganda avtomatik chaqiriladigan maxsus funksiya.  
U obyektning boshlang‘ich holatini belgilaydi.

    init(marka, tezlik, rang) ->
        this.brand = marka
        this.speed = tezlik
        this.colour = rang
    end
    
*Eslatma: Agar klassdan obyekt yaratilsa, `init` avtomatik ishga tushadi.*

**Inkapsulyatsiya**

Inkapsulyatsiya — bu obyekt ichidagi ma’lumotlarni va metodlarni bir joyga jamlash va tashqi tomondan bevosita kirishni cheklashdir.

-   Obyekt ma’lumotlari metodlar orqali boshqariladi
-   Kod xavfsiz va boshqariladigan bo‘ladi

Misol:

    func info() -> list
        return [this.brand, this.speed, this.colour]
    end

**Meros olish**

Meros olish — bir klassning boshqa klassdan xususiyat va metodlarni meros qilib olishi. `inherits` kalit so'zi bilan belgilanadi.

    class Tiko inherits Mashina ->
        init() ->
            this.brand = "Tiko"
            this.speed = 180
            this.colour = "Qizil"
        end
    end

Bu yerda:
-   `Tiko` — voris (child) klass
-   `Mashina` — ota/ona (parent) klass

**Polimorfizm**

Polimorfizm — bir xil metod nomi turli klasslarda turlicha ishlashi.
Metodni qayta yozish (override):

    func info() -> list
        return super.info()
    end
    
-   `super` — ota klassga murojaat qiladi
-   `info()` metodi `Tiko` klassida qayta yozilgan

To'liq misol:

    Mashina tiko = Tiko()
    output(tiko.info())
    
    Mashina car = Mashina("Gentra", 180, "Qora")
    output(car.info())

Bu yerda:
-   `tiko` — `Tiko` klassidan yaratilgan obyekt
-   `car` — `Mashina` klassidan yaratilgan obyekt
-   Ikkalasi ham `info()` metodiga ega (polimorfizm)

## Xatolar va istisnolar

Oryon tilida xatolarni boshqarish `try` konstruksiyasi orqali amalga oshiriladi. Bu mexanizm dastur bajarilishi davomida yuzaga keladigan xatolarni ushlash, qayta ishlash va yakuniy tozalash amallarini bajarish imkonini beradi.

**Asosiy sintaksis**

    try ->
        // xato chiqarishi mumkin bo‘lgan kod
    catch(e) ->
        // xatoni qayta ishlash
    finally ->
        // doimo bajariladigan kod
    end

`try` bloki:
Ushbu blok ichida xato (`exception`, istisno) yuz berishi mumkin bo‘lgan kod yoziladi.

    try ->
        throw "Error"
    end
    
*Eslatma: `try` operatori kamida bitta blok (`catch`, `catchonly` yoki `finally`) ga ega bo‘lishi shart. Aks holda bu sintaksis xatosi hisoblanadi.*

`throw` operatori:
Ushbu operator xato chiqarish uchun ishlatiladi.

    throw "Error"

Shuningdek, xato turi ham ko‘rsatilishi mumkin:

    throw "Error" -> "ErrorType"

Agar xato turi ko‘rsatilmasa, u avtomatik ravishda `"Exception"` deb belgilanadi.

`catch` bloki:
Ushbu blok `try` ichida yuzaga kelgan xatoni ushlaydi.

    catch(e) ->
        output(e)

`e` — xato xabari (error message)

**Xato turi bilan ishlash**

    catchonly(e, errtype) -> "ErrorType"
        output(e, errtype)

Bu `catchonly` faqat `"ErrorType"` turidagi xatolarni ushlaydi. Agar xato aniq tur bo‘yicha ushlanmasa, umumiy `catch` ishlaydi:

    catch(e, errtype) ->
        output("Uncaught by catchonly block", e, errtype)

`catchonly` bloki:
Ushbu blok maxsus xatolarni filtrlash uchun ishlatiladi.

    catchonly(e, errtype) -> "ErrorType"
        output(e, errtype)

Qoidalar:

-   `catchonly` bir nechta bo‘lishi mumkin
-   `catchonly` har doim `catch` va `finally`dan oldin joylashishi shart
-   `catch` va `finally` bloklari faqat bittadan bo‘lishi mumkin
-   `catch` bloki `finally`dan oldin kelishi shart

To‘g‘ri misol:

    try ->
        throw "Error" -> "TypeA"
    catchonly(e, errtype) -> "TypeA"
        output("TypeA error", e)
    catch ->
        output("Other error")
    finally ->
        output("Finally block")
    end

Noto‘g‘ri misol (sintaksis xatosi):

    try ->
    catch ->
    catchonly ->
    end

Sababi: `catchonly` `catch` dan keyin joylashgan.

`finally` bloki:
Ushbu blok har doim bajariladi, xato yuz berganidan qat’i nazar.

    finally ->
        output("Finally block")

`try` faqat `finally` bilan ham ishlashi mumkin:

    try ->
        throw "Error"
    finally ->
        output("Hech bo'lmaganda bu yerda men borman...")
    end

Bu holatda xato ushlanmaydi, lekin `finally` bajariladi.