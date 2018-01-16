from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import JsonResponse
from django.views.generic import DetailView, View
from django.views.generic.detail import SingleObjectMixin

from poetry.apps.corpus.models import Markup, MarkupVersion
from rupo.main.markup import Markup as TextMarkup
from rupo.util.preprocess import VOWELS


def process_markup(markup):
    text = markup.text
    output = []
    prev = 0
    for l in range(len(markup.lines)):
        line = markup.lines[l]
        output.append([])
        for w in range(len(line.words)):
            word = line.words[w]
            t = text[prev:word.begin]
            output[-1].append({'word': {'text': t}, 'word_number': -1})
            if len(word.syllables) == 0:
                output[-1].append({'word': {'text': word.text}, 'word_number': w})
            else:
                output[-1].append({'word': {'text': word.text, 'syllables': []}, 'word_number': w})
                accents_count = sum([1 for syllable in word.syllables if syllable.stress != -1])
                for s in range(len(word.syllables)):
                    syllable = word.syllables[s]
                    output[-1][-1]['word']['syllables'].append(
                        {'text': syllable.text, 'stress': syllable.stress,
                         'omography': accents_count > 1, 'no_accent': accents_count == 0})
            prev = word.end
        output[-1].append({'word': {'text': text[prev:line.end]}, 'word_number': -1})
        prev = line.end
    return output


class MarkupView(DetailView):
    model = Markup
    template_name = 'markup.html'
    context_object_name = 'markup'

    def get_context_data(self, **kwargs):
        context = super(MarkupView, self).get_context_data(**kwargs)
        markup = self.get_object()
        m = TextMarkup()
        m.from_json(markup.text)
        context['text'] = process_markup(m)
        context['poem'] = markup.poem
        context['poem'].name = markup.poem.get_name()
        context['lines_count'] = markup.poem.count_lines()
        context['additional'] = markup.get_automatic_additional()
        markups = set()
        for markup_instance in markup.poem.markups.all():
            markups.add(markup_instance.markup_version)
        context['markups'] = list(markups)
        return context

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            diffs = request.POST.getlist('diffs[]')

            m = self.get_object()
            poem = m.poem
            markup = m.get_markup()

            for diff in diffs:
                l = int(diff.split('-')[0])
                w = int(diff.split('-')[1])
                s = int(diff.split('-')[2])
                syllable = markup.lines[l].words[w].syllables[s]
                if syllable.stress != -1:
                    syllable.stress = -1
                else:
                    for i in range(len(syllable.text)):
                        if syllable.text[i] in VOWELS:
                            syllable.stress = syllable.begin + i

            m = Markup()
            m.text = markup.to_json()
            m.author = request.user.email
            m.poem = poem
            m.markup_version = MarkupVersion.objects.get(name="Manual")
            m.save()
            return JsonResponse({'url': reverse('corpus:markup', kwargs={'pk': m.pk}),},
                                status=200)
        else:
            raise PermissionDenied


class MarkupMakeStandardView(View, SingleObjectMixin):
    model = Markup

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated() and request.user.is_superuser:
            markup = self.get_object()
            for m in markup.poem.markups.all():
                m.is_standard = False
                m.save()
            markup.is_standard = True
            markup.save()
            return JsonResponse({'url': reverse('corpus:markup', kwargs={'pk': markup.pk}), }, status=200)
        else:
            raise PermissionDenied