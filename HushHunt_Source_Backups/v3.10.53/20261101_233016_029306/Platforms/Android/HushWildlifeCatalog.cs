#if ANDROID
using System;
using System.Collections.Generic;
using System.Linq;

namespace WhiskerHunt;

// HUSH_WILDLIFE_88_20261031: generated from Resources/Raw/wildlife/manifest.json.
// Keep this file and the JavaScript selector in sync with manifest.json.
internal static class HushWildlifeCatalog
{
    internal sealed record Entry(string Key, string Name, string Category, string AssetPath, bool Animated);
    // HUSH_31043_CATALOG_86: Lion uses the requested alternate animated GLB.
    private static readonly Dictionary<string, Entry> Entries = new(StringComparer.Ordinal)
    {
        ["hh3d-anteater"] = new("hh3d-anteater", "Anteater", "Wildlife", "wildlife/models/anteater.glb", false),
        ["hh3d-arctic-wolf"] = new("hh3d-arctic-wolf", "Arctic Wolf", "Wildlife", "wildlife/models/arctic_wolf.glb", true),
        ["hh3d-badger"] = new("hh3d-badger", "Badger", "Wildlife", "wildlife/models/badger.glb", false),
        ["hh3d-bat"] = new("hh3d-bat", "Bat", "Wildlife", "wildlife/models/bat.glb", false),
        ["hh3d-black-ant"] = new("hh3d-black-ant", "Black Ant", "Insects & Invertebrates", "wildlife/models/black_ant.glb", false),
        ["hh3d-bolognese-dog"] = new("hh3d-bolognese-dog", "Bolognese Dog", "Pets & Cats", "wildlife/models/bolognese_dog.glb", false),
        ["hh3d-camel"] = new("hh3d-camel", "Camel", "Wildlife", "wildlife/models/camel.glb", true),
        ["hh3d-capybara"] = new("hh3d-capybara", "Capybara", "Wildlife", "wildlife/models/capybara.glb", true),
        ["hh3d-capybara-static"] = new("hh3d-capybara-static", "Capybara (Static)", "Wildlife", "wildlife/models/capybara_static.glb", false),
        ["hh3d-celestial-deer"] = new("hh3d-celestial-deer", "Celestial Deer", "Fantasy", "wildlife/models/celestial_deer.glb", true),
        ["hh3d-celestial-fox"] = new("hh3d-celestial-fox", "Celestial Fox", "Fantasy", "wildlife/models/celestial_fox.glb", true),
        ["hh3d-celestial-stag"] = new("hh3d-celestial-stag", "Celestial Stag", "Fantasy", "wildlife/models/celestial_stag.glb", false),
        ["hh3d-chill-guy-kangaroo"] = new("hh3d-chill-guy-kangaroo", "Chill Guy Kangaroo", "Fantasy", "wildlife/models/chill_guy_kangaroo.glb", false),
        ["hh3d-chimpanzee"] = new("hh3d-chimpanzee", "Chimpanzee", "Wildlife", "wildlife/models/chimpanzee.glb", false),
        ["hh3d-chow-chow-dog"] = new("hh3d-chow-chow-dog", "Chow Chow Dog", "Pets & Cats", "wildlife/models/chow_chow_dog.glb", true),
        ["hh3d-corgi"] = new("hh3d-corgi", "Corgi", "Pets & Cats", "wildlife/models/corgi.glb", true),
        ["hh3d-donkey"] = new("hh3d-donkey", "Donkey", "Wildlife", "wildlife/models/donkey.glb", true),
        ["hh3d-donkey-static"] = new("hh3d-donkey-static", "Donkey (Static)", "Wildlife", "wildlife/models/donkey_static.glb", false),
        ["hh3d-drog-dog-meme"] = new("hh3d-drog-dog-meme", "Drog Dog Meme", "Pets & Cats", "wildlife/models/drog_dog_meme.glb", true),
        ["hh3d-eagle"] = new("hh3d-eagle", "Eagle", "Birds", "wildlife/models/eagle.glb", false),
        ["hh3d-elephant"] = new("hh3d-elephant", "Elephant", "Wildlife", "wildlife/models/elephant.glb", false),
        ["hh3d-emerald-chameleon"] = new("hh3d-emerald-chameleon", "Emerald Chameleon", "Reptiles & Amphibians", "wildlife/models/emerald_chameleon.glb", false),
        ["hh3d-emerald-dragonfly"] = new("hh3d-emerald-dragonfly", "Emerald Dragonfly", "Fantasy", "wildlife/models/emerald_dragonfly.glb", false),
        ["hh3d-falcon"] = new("hh3d-falcon", "Falcon", "Birds", "wildlife/models/falcon.glb", false),
        ["hh3d-fennec-fox"] = new("hh3d-fennec-fox", "Fennec Fox", "Wildlife", "wildlife/models/fennec_fox.glb", false),
        ["hh3d-fishing-squirrel"] = new("hh3d-fishing-squirrel", "Fishing Squirrel", "Wildlife", "wildlife/models/fishing_squirrel.glb", false),
        ["hh3d-flamingo"] = new("hh3d-flamingo", "Flamingo", "Birds", "wildlife/models/flamingo.glb", false),
        ["hh3d-frog"] = new("hh3d-frog", "Frog", "Reptiles & Amphibians", "wildlife/models/frog.glb", false),
        ["hh3d-fruit-bat"] = new("hh3d-fruit-bat", "Fruit Bat", "Wildlife", "wildlife/models/fruit_bat.glb", false),
        ["hh3d-gecko"] = new("hh3d-gecko", "Gecko", "Reptiles & Amphibians", "wildlife/models/gecko.glb", false),
        ["hh3d-german-spitz-dog"] = new("hh3d-german-spitz-dog", "German Spitz Dog", "Pets & Cats", "wildlife/models/german_spitz_dog.glb", false),
        ["hh3d-ginger-tabby-cat"] = new("hh3d-ginger-tabby-cat", "Ginger Tabby Cat", "Pets & Cats", "wildlife/models/ginger_tabby_cat.glb", false),
        ["hh3d-giraffe"] = new("hh3d-giraffe", "Giraffe", "Wildlife", "wildlife/models/giraffe.glb", true),
        ["hh3d-golden-retriever"] = new("hh3d-golden-retriever", "Golden Retriever", "Pets & Cats", "wildlife/models/golden_retriever.glb", true),
        ["hh3d-grey-squirrel"] = new("hh3d-grey-squirrel", "Grey Squirrel", "Wildlife", "wildlife/models/grey_squirrel.glb", false),
        ["hh3d-hare"] = new("hh3d-hare", "Hare", "Wildlife", "wildlife/models/hare.glb", false),
        ["hh3d-hawk"] = new("hh3d-hawk", "Hawk", "Birds", "wildlife/models/hawk.glb", false),
        ["hh3d-hedgehog"] = new("hh3d-hedgehog", "Hedgehog", "Wildlife", "wildlife/models/hedgehog.glb", false),
        ["hh3d-honey-bee"] = new("hh3d-honey-bee", "Honey Bee", "Insects & Invertebrates", "wildlife/models/honey_bee.glb", false),
        ["hh3d-jack-russell-dog"] = new("hh3d-jack-russell-dog", "Jack Russell Dog", "Pets & Cats", "wildlife/models/jack_russell_dog.glb", true),
        ["hh3d-jack-russell-terrier"] = new("hh3d-jack-russell-terrier", "Jack Russell Terrier", "Pets & Cats", "wildlife/models/jack_russell_terrier.glb", true),
        ["hh3d-japanese-macaque"] = new("hh3d-japanese-macaque", "Japanese Macaque", "Wildlife", "wildlife/models/japanese_macaque.glb", false),
        ["hh3d-kangaroo"] = new("hh3d-kangaroo", "Kangaroo", "Wildlife", "wildlife/models/kangaroo.glb", false),
        ["hh3d-kangaroo-mouse"] = new("hh3d-kangaroo-mouse", "Kangaroo Mouse", "Wildlife", "wildlife/models/kangaroo_mouse.glb", false),
        ["hh3d-koala"] = new("hh3d-koala", "Koala", "Wildlife", "wildlife/models/koala.glb", false),
        ["hh3d-labrador"] = new("hh3d-labrador", "Labrador", "Pets & Cats", "wildlife/models/labrador.glb", true),
        ["hh3d-ladybug"] = new("hh3d-ladybug", "Ladybug", "Insects & Invertebrates", "wildlife/models/ladybug.glb", false),
        ["hh3d-lemur"] = new("hh3d-lemur", "Lemur", "Wildlife", "wildlife/models/lemur.glb", false),
        ["hh3d-lion"] = new("hh3d-lion", "Lion", "Wildlife", "wildlife/models/lion_alternate.glb", true),
        ["hh3d-lioness"] = new("hh3d-lioness", "Lioness", "Wildlife", "wildlife/models/lioness.glb", false),
        ["hh3d-mandarin-duck"] = new("hh3d-mandarin-duck", "Mandarin Duck", "Birds", "wildlife/models/mandarin_duck.glb", false),
        ["hh3d-meerkat"] = new("hh3d-meerkat", "Meerkat", "Wildlife", "wildlife/models/meerkat.glb", false),
        ["hh3d-mouse"] = new("hh3d-mouse", "Mouse", "Wildlife", "wildlife/models/mouse.glb", false),
        ["hh3d-nebula-butterfly"] = new("hh3d-nebula-butterfly", "Nebula Butterfly", "Fantasy", "wildlife/models/nebula_butterfly.glb", false),
        ["hh3d-nine-tails-fox-black"] = new("hh3d-nine-tails-fox-black", "Nine Tails Fox Black", "Fantasy", "wildlife/models/nine_tails_fox_black.glb", false),
        ["hh3d-nine-tails-fox-white"] = new("hh3d-nine-tails-fox-white", "Nine Tails Fox White", "Fantasy", "wildlife/models/nine_tails_fox_white.glb", false),
        ["hh3d-octopus"] = new("hh3d-octopus", "Octopus", "Marine & Invertebrates", "wildlife/models/octopus.glb", false),
        ["hh3d-orangutan"] = new("hh3d-orangutan", "Orangutan", "Wildlife", "wildlife/models/orangutan.glb", false),
        ["hh3d-owl"] = new("hh3d-owl", "Owl", "Birds", "wildlife/models/owl.glb", false),
        ["hh3d-pallas-cat"] = new("hh3d-pallas-cat", "Pallas Cat", "Pets & Cats", "wildlife/models/pallas_cat.glb", false),
        ["hh3d-peacock"] = new("hh3d-peacock", "Peacock", "Birds", "wildlife/models/peacock.glb", false),
        ["hh3d-peacock-pink"] = new("hh3d-peacock-pink", "Peacock Pink", "Birds", "wildlife/models/peacock_pink.glb", false),
        ["hh3d-pelican"] = new("hh3d-pelican", "Pelican", "Birds", "wildlife/models/pelican.glb", false),
        ["hh3d-phoenix"] = new("hh3d-phoenix", "Phoenix", "Fantasy", "wildlife/models/phoenix.glb", false),
        ["hh3d-pitbull-dog"] = new("hh3d-pitbull-dog", "Pitbull Dog", "Pets & Cats", "wildlife/models/pitbull_dog.glb", true),
        ["hh3d-rabbit"] = new("hh3d-rabbit", "Rabbit", "Wildlife", "wildlife/models/rabbit.glb", false),
        ["hh3d-ragdoll-cat-brown"] = new("hh3d-ragdoll-cat-brown", "Ragdoll Cat (Brown)", "Pets & Cats", "wildlife/models/ragdoll_cat_brown.glb", false),
        ["hh3d-ragdoll-cat-grey"] = new("hh3d-ragdoll-cat-grey", "Ragdoll Cat (Grey)", "Pets & Cats", "wildlife/models/ragdoll_cat_grey.glb", true),
        ["hh3d-red-panda"] = new("hh3d-red-panda", "Red Panda", "Wildlife", "wildlife/models/red_panda.glb", true),
        ["hh3d-reindeer"] = new("hh3d-reindeer", "Reindeer", "Wildlife", "wildlife/models/reindeer.glb", false),
        ["hh3d-rhinoceros"] = new("hh3d-rhinoceros", "Rhinoceros", "Wildlife", "wildlife/models/rhinoceros.glb", true),
        ["hh3d-seal-baby"] = new("hh3d-seal-baby", "Seal Baby", "Wildlife", "wildlife/models/seal_baby.glb", true),
        ["hh3d-shiba-inu-dog"] = new("hh3d-shiba-inu-dog", "Shiba Inu Dog", "Pets & Cats", "wildlife/models/shiba_inu_dog.glb", true),
        ["hh3d-silverback-gorilla"] = new("hh3d-silverback-gorilla", "Silverback Gorilla", "Wildlife", "wildlife/models/silverback_gorilla.glb", true),
        ["hh3d-slug"] = new("hh3d-slug", "Slug", "Marine & Invertebrates", "wildlife/models/slug.glb", false),
        ["hh3d-snail"] = new("hh3d-snail", "Snail", "Marine & Invertebrates", "wildlife/models/snail.glb", false),
        ["hh3d-snow-leopard"] = new("hh3d-snow-leopard", "Snow Leopard", "Wildlife", "wildlife/models/snow_leopard.glb", true),
        ["hh3d-snow-monkey-on-bamboo"] = new("hh3d-snow-monkey-on-bamboo", "Snow Monkey On Bamboo", "Wildlife", "wildlife/models/snow_monkey_on_bamboo.glb", false),
        ["hh3d-spider"] = new("hh3d-spider", "Spider", "Insects & Invertebrates", "wildlife/models/spider.glb", false),
        ["hh3d-stag"] = new("hh3d-stag", "Stag", "Wildlife", "wildlife/models/stag.glb", true),
        ["hh3d-stag-beetle"] = new("hh3d-stag-beetle", "Stag Beetle", "Insects & Invertebrates", "wildlife/models/stag_beetle.glb", false),
        ["hh3d-tabby-cat"] = new("hh3d-tabby-cat", "Tabby Cat", "Pets & Cats", "wildlife/models/tabby_cat.glb", true),
        ["hh3d-three-headed-dragon"] = new("hh3d-three-headed-dragon", "Three-Headed Dragon", "Fantasy", "wildlife/models/three_headed_dragon.glb", false),
        ["hh3d-thunderbird"] = new("hh3d-thunderbird", "Thunderbird", "Fantasy", "wildlife/models/thunderbird.glb", false),
        ["hh3d-turtle"] = new("hh3d-turtle", "Turtle", "Reptiles & Amphibians", "wildlife/models/turtle.glb", true),
        ["hh3d-tuxedo-cat"] = new("hh3d-tuxedo-cat", "Tuxedo Cat", "Pets & Cats", "wildlife/models/tuxedo_cat.glb", true),
        ["hh3d-wasp"] = new("hh3d-wasp", "Wasp", "Insects & Invertebrates", "wildlife/models/wasp.glb", false),
        ["hh3d-wild-boar"] = new("hh3d-wild-boar", "Wild Boar", "Wildlife", "wildlife/models/wild_boar.glb", true),
        ["hh3d-wolf"] = new("hh3d-wolf", "Wolf", "Wildlife", "wildlife/models/wolf.glb", true),
    };

    internal static bool TryGet(string modelKey, out Entry? selected)
    {
        var found = Entries.TryGetValue(modelKey, out var entry);
        selected = entry;
        return found;
    }

    internal static float RecommendedSizeMetres(string name, string category)
    {
        // Relative scale of the longest GLB bounding-box dimension; user can resize in AR.
        var n = name.ToLowerInvariant();
        if (n.Contains("elephant") || n.Contains("giraffe")) return 1.4f;
        if (n.Contains("dragon") || n.Contains("camel") || n.Contains("rhinoceros")) return 1.15f;
        if (n.Contains("gorilla") || n.Contains("lion") || n.Contains("wolf") || n.Contains("reindeer")) return .9f;
        if (n.Contains("dog") || n.Contains("retriever") || n.Contains("labrador") || n.Contains("corgi") || n.Contains("terrier") || n.Contains("pitbull") || n.Contains("shiba")) return .65f;
        if (n.Contains("cat") || n.Contains("pallas") || n.Contains("fox") || n.Contains("panda")) return .47f;
        // HUSH_31040_SQUIRREL_SIZE: longest-dimension target in metres.
        if (n.Contains("squirrel")) return .28f;
        if (n.Contains("mouse") || n.Contains("ladybug") || n.Contains("ant") || n.Contains("bee") || n.Contains("wasp") || n.Contains("beetle") || n.Contains("butterfly") || n.Contains("dragonfly")) return .16f;
        if (category == "Birds") return .4f;
        return .6f;
    }
}
#endif
