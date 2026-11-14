"""A wallet's three word name ("ember · gravel · paddle"), the same as on its feeder card (share/cards.py words());
a copy, as the alerts image holds only alerts/*.py. test_agorzilla.py checks the two lists stay the same."""
from __future__ import annotations

import hashlib

WORDS = (
    'acorn amber anchor apple arrow atlas badge baker bamboo banjo barley basil beacon beaver berry bison blade '
    'blossom bonnet bottle bramble breeze brick bridge bronze brook bucket bugle cabin cactus camel candle canoe '
    'canyon carbon carrot castle cedar cello chalk cherry chess cider cinder circus clover cobalt comet copper '
    'coral cotton cougar crane crater cricket crystal cupola dahlia daisy delta denim desert dingo dolphin dragon '
    'drum eagle easel ember emerald engine falcon feather fennel fern fiddle flint forest fossil fox galaxy '
    'garden garnet gecko geyser ginger glacier goblet granite grape gravel guitar hammer harbor harp hazel heron '
    'hickory honey hornet husky iceberg igloo indigo iris island ivory jackal jade jaguar jasmine jelly jigsaw '
    'jungle kayak kernel kettle kiwi koala ladder lagoon lantern laurel lemon lilac lily linen lizard lobster '
    'locket lotus magnet mango maple marble meadow melon meteor mint mitten mosaic moss muffin nectar needle '
    'nickel nutmeg oak oasis olive onyx orbit orchid otter oyster paddle panda papaya parrot pebble pecan pelican '
    'pepper piano pine planet plum pollen poppy prism puffin pumpkin quartz quill rabbit radish raven reef ribbon '
    'river robin rocket rose ruby saddle saffron salmon sapphire satin shell sierra silver sparrow spruce squid '
    'statue stone summit sunset swan tango teapot thistle thunder tiger timber toucan tractor trumpet tulip '
    'tundra turtle umbrella valley velvet violet volcano walnut walrus willow window winter wizard yarrow yogurt '
    'zebra zenith zinc basket beetle bobcat cocoa cobra dune elm glove gopher jasper lark mammoth marsh opal '
    'osprey parsley quail rhubarb sable sequoia stork tapir topaz trout vanilla wombat yak nomad '
).split()




def words(a: str) -> str:
    h = hashlib.sha256(a.encode()).digest()
    return " · ".join(WORDS[x] for x in h[8:11])
