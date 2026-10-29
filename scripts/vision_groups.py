"""Map the 1000 ImageNet classes the network predicts onto the photographic genres Darkroom edits for.

The network does the recognising (it was trained on 1.2 M labelled photos); this table only says which
classes mean 'a landscape', 'a building', 'food', and so on."""
import json
import sys

LANDSCAPE = """alp volcano cliff promontory valley geyser coral_reef seashore sandbar lakeside breakwater
rapeseed daisy hay corn bubble earthworm yellow_lady's_slipper""".replace("\n", " ").split()
SEA = "seashore sandbar lakeside breakwater pier dock speedboat catamaran trimaran schooner yawl gondola canoe paddle container_ship liner fireboat lifeboat wreck aircraft_carrier submarine boathouse".split()
ARCH = """palace church monastery mosque castle triumphal_arch barn cinema library greenhouse planetarium prison obelisk lighthouse
bell_cote steel_arch_bridge suspension_bridge viaduct dam water_tower windmill totem_pole altar mobile_home tile_roof thatch
cliff_dwelling yurt igloo megalith pedestal stupa solar_dish bannister scoreboard flagpole boathouse beacon fountain""".replace("\n", " ").split()
INTERIOR = """dining_table studio_couch sliding_door window_shade wardrobe bookcase fireplace rocking_chair throne quilt four-poster crib cradle
home_theater monitor desk file entertainment_center barber_chair washbasin medicine_chest china_cabinet stove refrigerator dishwasher
microwave pillow lampshade table_lamp prayer_rug doormat folding_chair chiffonier plate_rack wall_clock grandfather_clock mosquito_net
theater_curtain shower_curtain bathtub tub toilet_seat espresso_maker Dutch_oven window_screen""".replace("\n", " ").split()
STREET = """street_sign traffic_light parking_meter cab minivan trolleybus school_bus police_van streetcar bicycle-built-for-two mountain_bike moped
motor_scooter pay-phone turnstile manhole_cover umbrella shopping_cart mailbag mailbox fire_engine garbage_truck tow_truck trailer_truck pickup
limousine convertible sports_car racer Model_T jeep go-kart golfcart tricycle unicycle bakery barbershop bookshop butcher_shop
candy_store confectionery grocery_store shoe_shop tobacco_shop toyshop restaurant park_bench patio
""".replace("\n", " ").split()
PERSON = """groom scuba_diver ballplayer suit sweatshirt cardigan lab_coat kimono abaya gown miniskirt bikini maillot swimming_trunks
cowboy_hat sombrero mortarboard bow_tie Windsor_tie military_uniform fur_coat poncho overskirt hoopskirt pajama sarong academic_gown
cloak stole bonnet mask wig lipstick face_powder hair_spray apron jean brassiere bathing_cap feather_boa Loafer sandal cowboy_boot
running_shoe sock clog bulletproof_vest cuirass chain_mail jersey velvet fur_coat""".replace("\n", " ").split()
FOOD_RANGE = range(923, 970)
FOOD_EXTRA = "coffee_mug beer_glass wine_bottle water_jug cocktail_shaker wok frying_pan soup_bowl mixing_bowl ladle spatula measuring_cup teapot goblet".split()


def groups(labels):
    norm = [l.lower().replace(" ", "_") for l in labels]
    idx = {n: i for i, n in enumerate(norm)}
    find = lambda names: sorted({idx[n.lower()] for n in names if n.lower() in idx})  # noqa: E731
    g = {"landscape": find(LANDSCAPE), "sea": find(SEA), "architecture": find(ARCH), "interior": find(INTERIOR),
         "street": find(STREET), "person": find(PERSON),
         "food": sorted((set(FOOD_RANGE) - {958}) | set(find(FOOD_EXTRA))),
         "animal": list(range(0, 398))}
    return g


if __name__ == "__main__":
    labels = json.load(open(sys.argv[1]))["labels"]
    g = groups(labels)
    if len(sys.argv) > 2:
        for k, v in g.items():
            print(k, len(v), [labels[i] for i in v][:60])
    else:
        json.dump(g, sys.stdout, separators=(",", ":"))
