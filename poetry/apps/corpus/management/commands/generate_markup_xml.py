# -*- coding: utf-8 -*-
import os

from django.core.management.base import BaseCommand
from poetry.settings import BASE_DIR
from poetry.apps.corpus.scripts.phonetics.accent_classifier import AccentClassifier
from poetry.apps.corpus.scripts.phonetics.accent_dict import AccentDict
from poetry.apps.corpus.scripts.metre.metre_classifier import MetreClassifier
from poetry.apps.corpus.models import Poem, Markup
from poetry.apps.corpus.scripts.phonetics.phonetics import Phonetics


class Command(BaseCommand):
    help = 'Automatic markup update'

    def handle(self, *args, **options):
        accents_dict = AccentDict(os.path.join(BASE_DIR, "datasets", "dicts", "accents_dict"))
        accents_classifier = AccentClassifier(os.path.join(BASE_DIR, "datasets", "models"), accents_dict)
        i = 1
        with open(os.path.join(BASE_DIR, "datasets", "corpus", "markup_dump.xml"), "wb") as f:
            f.write(b'<?xml version="1.0" encoding="UTF-8"?><items>')
            for p in Poem.objects.all():
                markup = Phonetics.process_text(p.text, accents_dict)
                markup, result = MetreClassifier.improve_markup(markup, accents_classifier)
                xml = markup.to_xml().encode('utf-8').replace(b'<?xml version="1.0" encoding="UTF-8" ?>', b'')\
                    .decode('utf-8').replace("\n", "\\n").replace('"', '\\"').replace("\t", "\\t").encode('utf-8')
                f.write(xml)
                i += 1
                if i % 100 == 0:
                    print(i)
            f.write(b'</items>')
