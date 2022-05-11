import uma
from bs4 import BeautifulSoup

articles = uma.get_latest_news()
for article in articles:
    print("="*20)
    print(article["title"])
    soup = BeautifulSoup(article["message"], "html.parser")
    img = soup.find('img')
    if img:
        print(img["src"])

quit()

import mal_tools as mal
import database_tools as db


conn, cursor = db.get_connection()

cursor.execute("""select w.id, i.character_id from images i
JOIN waifus w on w.images_id = i.id
where normal_url is null;
""")
rows = cursor.fetchall()
for row in rows:
    waifu_id = row[0]
    char_id = row[1]


conn.commit()
conn.close()


db.removeUselessWaifus()

mal.downloadInsertShowCharacters("")

mal.downloadInsertShowCharacters("https://myanimelist.net/manga/7519/Kami_nomi_zo_Shiru_Sekai/")
mal.downloadInsertShowCharacters("https://myanimelist.net/manga/123450/Saikin_Yatotta_Maid_ga_Ayashii")
mal.downloadInsertShowCharacters("https://myanimelist.net/manga/138079/Genshin_Comic_Anthology")

mal.downloadInsertShowCharacters("https://myanimelist.net/anime/33573/BanG_Dream")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/48753/Jahy-sama_wa_Kujikenai")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/48556/Takt_Op_Destiny")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/22147/Amagi_Brilliant_Park")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/10721/Mawaru_Penguindrum")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/16732/Kiniro_Mosaic")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/10495/Yuru_Yuri")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/36259/Pingu_in_the_City")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/37430/Tensei_shitara_Slime_Datta_Ken")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/39551/Tensei_shitara_Slime_Datta_Ken_2nd_Season")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/10165/Nichijou")
mal.downloadInsertShowCharacters("https://myanimelist.net/manga/3446/Maker_Hikoushiki_Hatsune_Mix")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/43299/Wonder_Egg_Priority")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/33489/Little_Witch_Academia_TV")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/6594/Katanagatari")
mal.downloadInsertShowCharacters("https://myanimelist.net/manga/34053/Umineko_no_Naku_Koro_ni_Chiru_-_Episode_8__Twilight_of_the_Golden_Witch")
mal.downloadInsertShowCharacters("https://myanimelist.net/manga/16144/Umineko_no_Naku_Koro_ni_-_Episode_4__Alliance_of_the_Golden_Witch")
mal.downloadInsertShowCharacters("http://www.myanimelist.net/anime/33674/No_Game_No_Life__Zero")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/13601/Psycho-Pass")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/2966/Ookami_to_Koushinryou")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/5341/Ookami_to_Koushinryou_II")
#mal.downloadInsertShowCharacters("https://myanimelist.net/anime/33255/Saiki_Kusuo_no_%CE%A8-nan")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/41457/86")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/48569/86_Part_2")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/25777/Shingeki_no_Kyojin_Season_2")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/40591/Kaguya-sama_wa_Kokurasetai__Tensai-tachi_no_Renai_Zunousen")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/31716/Rewrite")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/30307/Monster_Musume_no_Iru_Nichijou")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/36633/Date_A_Live_III")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/41006/Higurashi_no_Naku_Koro_ni_Gou")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/14131/Girls___Panzer")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/39247/Kobayashi-san_Chi_no_Maid_Dragon_S")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/10087/Fate_Zero")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/33263/Kubikiri_Cycle__Aoiro_Savant_to_Zaregototsukai")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/35760/Shingeki_no_Kyojin_Season_3")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/14813/Yahari_Ore_no_Seishun_Love_Comedy_wa_Machigatteiru")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/23847/Yahari_Ore_no_Seishun_Love_Comedy_wa_Machigatteiru_Zoku")
# mal.downloadInsertShowCharacters("https://myanimelist.net/manga/121523/Fire_Emblem_Heroes__Eiyuu-tachi_no_Nichijou")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/10012/Carnival_Phantasm")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/41307/Tokyo_7th_Sisters__Bokura_wa_Aozora_ni_Naru")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/35503/Shoujo%E2%98%86Kageki_Revue_Starlight")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/40571/Majo_no_Tabitabi")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/38005/Strike_Witches__Road_to_Berlin")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/32866/Brave_Witches")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/35983/Harukana_Receive")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/44274/Puraore_Pride_of_Orange")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/9260/Kizumonogatari_I__Tekketsu-hen")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/31757/Kizumonogatari_II__Nekketsu-hen")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/31758/Kizumonogatari_III__Reiketsu-hen")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/5081/Bakemonogatari?q=bakemonogatari&cat=anime")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/11597/Nisemonogatari?q=nisemonog&cat=anime")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/15689/Nekomonogatari__Kuro?q=monogatari&cat=anime")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/17074/Monogatari_Series__Second_Season?q=monog&cat=anime")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/28025/Tsukimonogatari?q=tsuki&cat=anime")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/21855/Hanamonogatari?q=hana&cat=anime")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/31181/Owarimonogatari?q=owari&cat=anime")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/35247/Owarimonogatari_2nd_Season?q=owari&cat=anime")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/36999/Zoku_Owarimonogatari?q=zoku%20owari&cat=anime")
mal.downloadInsertShowCharacters("https://myanimelist.net/manga/91941/Made_in_Abyss?q=made%20in%20abyss&cat=manga")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/5114/Fullmetal_Alchemist__Brotherhood?q=full%20metal%20alchemist&cat=anime")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/205/Samurai_Champloo?q=samurai%20cham&cat=anime")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/18679/Kill_la_Kill?q=kill&cat=anime")
mal.downloadInsertShowCharacters("https://myanimelist.net/manga/108495/NieR_Automata?q=nier&cat=manga")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/38573/Tsuujou_Kougeki_ga_Zentai_Kougeki_de_Ni-kai_Kougeki_no_Okaasan_wa_Suki_Desu_ka")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/10012/Carnival_Phantasm")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/44042/Holo_no_Graffiti")
mal.downloadInsertShowCharacters("https://myanimelist.net/manga/5376/Touhou_Gumonshiki__Memorizable_Gensokyo")
mal.downloadInsertShowCharacters("https://myanimelist.net/manga/175/Touhou_Sangetsusei__Eastern_and_Little_Nature_Deity")
mal.downloadInsertShowCharacters("https://myanimelist.net/manga/11929/Touhou_Sangetsusei__Strange_and_Bright_Nature_Deity")
mal.downloadInsertShowCharacters("https://myanimelist.net/manga/14439/Touhou_Sangetsusei__Oriental_Sacred_Place")
mal.downloadInsertShowCharacters("https://myanimelist.net/manga/96369/Touhou_Sangetsusei__Visionary_Fairies_in_Shrine")
mal.downloadInsertShowCharacters("https://myanimelist.net/manga/3014/Touhou_Bougetsushou__Silent_Sinner_in_Blue")
mal.downloadInsertShowCharacters("https://myanimelist.net/manga/5373/Touhou_Bougetsushou__Cage_in_Lunatic_Runagate")
mal.downloadInsertShowCharacters("https://myanimelist.net/manga/9429/Touhou_Bougetsushou__Tsuki_no_Inaba_to_Chijou_no_Inaba")
mal.downloadInsertShowCharacters("https://myanimelist.net/manga/21054/Touhou_Ibara_Kasen__Wild_and_Horned_Hermit")
mal.downloadInsertShowCharacters("https://myanimelist.net/manga/44523/Touhou_Suzunaan__Forbidden_Scrollery")
mal.downloadInsertShowCharacters("https://myanimelist.net/manga/123038/Touhou_Suichouka__Lotus_Eater-tachi_no_Suisei")
mal.downloadInsertShowCharacters("https://myanimelist.net/manga/122572/Touhou_Chireikiden__Hansoku_Tantei_Satori")
mal.downloadInsertShowCharacters("https://myanimelist.net/manga/14466/Touhou_Kourindou__Curiosities_of_Lotus_Asia")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/38853/Ex-Arm")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/46095/Vivy__Fluorite_Eyes_Song")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/35839/Sora_yori_mo_Tooi_Basho")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/849/Suzumiya_Haruhi_no_Yuuutsu")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/40550/Assault_Lily__Bouquet")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/11867/Cipher")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/35849/Darling_in_the_FranXX")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/28221/Etotama")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/20541/Mikakunin_de_Shinkoukei")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/31953/New_Game")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/66/Azumanga_Daioh")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/934/Higurashi_no_Naku_Koro_ni")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/9756/Mahou_Shoujo_Madoka%E2%98%85Magica")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/39535/Mushoku_Tensei__Isekai_Ittara_Honki_Dasu")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/5042/Kiss_x_Sis")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/18041/Rozen_Maiden_2013")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/30/Neon_Genesis_Evangelion")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/33352/Violet_Evergarden")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/43439/Shadows_House")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/3455/To_LOVE-Ru")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/4224/Toradora")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/1195/Zero_no_Tsukaima")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/31646/3-gatsu_no_Lion")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/42653/Aikatsu_Planet")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/44275/Selection_Project")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/40842/Idoly_Pride")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/40148/22_7")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/39071/Machikado_Mazoku")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/623/Shichinin_no_Nana")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/30831/Kono_Subarashii_Sekai_ni_Shukufuku_wo")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/32937/Kono_Subarashii_Sekai_ni_Shukufuku_wo_2")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/27441/Show_By_Rock")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/32038/Show_By_Rock_")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/38009/Re_Stage_Dream_Days%E2%99%AA")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/11785/Haiyore_Nyaruko-san")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/15699/Haiyore_Nyaruko-san_W")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/40763/Show_By_Rock_Mashumairesh")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/41520/Show_by_Rock_Stars")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/39681/D4DJ__First_Mix")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/39292/Princess_Connect_Re_Dive")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/13659/Ore_no_Imouto_ga_Konnani_Kawaii_Wake_ga_Nai")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/34798/Yuru_Camp%E2%96%B3")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/38474/Yuru_Camp%E2%96%B3_Season_2")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/32268/Koyomimonogatari")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/9253/Steins_Gate")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/19815/No_Game_No_Life")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/383/Galaxy_Angel")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/38992/Rikei_ga_Koi_ni_Ochita_no_de_Shoumei_shitemita")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/1887/Lucky%E2%98%86Star")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/2167/Clannad")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/4181/Clannad__After_Story")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/14741/Chuunibyou_demo_Koi_ga_Shitai")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/18671/Chuunibyou_demo_Koi_ga_Shitai_Ren")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/11751/Senki_Zesshou_Symphogear")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/15793/Senki_Zesshou_Symphogear_G")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/21573/Senki_Zesshou_Symphogear_GX")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/32836/Senki_Zesshou_Symphogear_AXZ")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/32843/Senki_Zesshou_Symphogear_XV")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/21273/Gochuumon_wa_Usagi_Desu_ka")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/29787/Gochuumon_wa_Usagi_Desu_ka")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/35249/Uma_Musume__Pretty_Derby_TV")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/37916/Uma_Musume__Pretty_Derby_-_BNW_no_Chikai")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/42941/Uma_Musume__Pretty_Derby_TV_Season_2")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/16157/Choujigen_Game_Neptune_The_Animation")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/15051/Love_Live_School_Idol_Project")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/32526/Love_Live_Sunshine")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/40879/Love_Live_Nijigasaki_Gakuen_School_Idol_Doukoukai")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/41169/Love_Live_Superstar")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/30547/Touhou_Niji_Sousaku_Doujin_Anime__Musou_Kakyou_Special")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/9874/Touhou_Niji_Sousaku_Doujin_Anime__Musou_Kakyou")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/36686/Hifuu_Katsudou_Kiroku__The_Sealed_Esoteric_History")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/32901/Eromanga-sensei")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/8769/Ore_no_Imouto_ga_Konnani_Kawaii_Wake_ga_Nai")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/6547/Angel_Beats")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/28999/Charlotte")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/16706/Kami_nomi_zo_Shiru_Sekai__Megami-hen")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/21085/Witch_Craft_Works")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/13759/Sakura-sou_no_Pet_na_Kanojo")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/27775/Plastic_Memories")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/8525/Kami_nomi_zo_Shiru_Sekai")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/10080/Kami_nomi_zo_Shiru_Sekai_II")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/15117/Kami_nomi_zo_Shiru_Sekai__Tenri-hen")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/31240/Re_Zero_kara_Hajimeru_Isekai_Seikatsu")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/42203/Re_Zero_kara_Hajimeru_Isekai_Seikatsu_2nd_Season_Part_2")
mal.downloadInsertShowCharacters("https://myanimelist.net/anime/39587/Re_Zero_kara_Hajimeru_Isekai_Seikatsu_2nd_Season")

db.createDatabase()

db.insertCharacter(mal.downloadCharacter(13468))
db.insertCharacter(mal.downloadCharacter(14015))
db.insertCharacter(mal.downloadCharacter(18866))
db.insertCharacter(mal.downloadCharacter(22306))
db.insertCharacter(mal.downloadCharacter(15636))
db.insertCharacter(mal.downloadCharacter(15449))
db.insertCharacter(mal.downloadCharacter(22322))
db.insertCharacter(mal.downloadCharacter(26275))
db.insertCharacter(mal.downloadCharacter(61371))
db.insertCharacter(mal.downloadCharacter(64167))
db.insertCharacter(mal.downloadCharacter(64173))
db.insertCharacter(mal.downloadCharacter(64169))
db.insertCharacter(mal.downloadCharacter(64165))
db.insertCharacter(mal.downloadCharacter(22037))
db.insertCharacter(mal.downloadCharacter(109213), alt_name="trash")
db.insertCharacter(mal.downloadCharacter(8128))
db.insertCharacter(mal.downloadCharacter(25170))
db.insertCharacter(mal.downloadCharacter(16192))
db.insertCharacter(mal.downloadCharacter(25171))
db.insertCharacter(mal.downloadCharacter(16193))
db.insertCharacter(mal.downloadCharacter(25169))
db.insertCharacter(mal.downloadCharacter(16194))
db.insertCharacter(mal.downloadCharacter(38940), alt_name="nae nae")
db.insertCharacter(mal.downloadCharacter(110137))
