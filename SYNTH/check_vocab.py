"""Check candidate SYNTH vocabulary against the scorer's known vocabulary."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import score_esperanto_text as s

roots, words = s.load_vocabulary()
print('roots:', len(roots), 'words:', len(words))

CANDS = """saluton tagon bonan vesperon jes ne dankon bonvolu mi vi li ŝi ni ili
esti estas estis estos havas havis faras faris faros farita preta pretas tasko taskojn
laboro laboras laboris tempo horo horojn tago semajno hodiaŭ morgaŭ nun baldaŭ
tuj poste eble certe kompreneble raporton raporto staton problemo problemojn
eraro erarojn servo servilo dosiero dosierojn mesaĝo mesaĝon sendi sendu sendis
ricevi ricevis komenci komencis komencos fini finis finita atendi atendas helpi
helpas bezonas bezonis volas povas povos devas devus
unu du tri kvar kvin ses sep ok naŭ dek dudek cent mil
nomo nomon teamo teamon alano beto kiel fartas fartos bone tre bona plej
rapide malrapide grava urgenta facila malfacila nova malnova granda malgranda
skribi skribis legi legis respondi respondu respondis demandi demando
planas provas sukcesis sukcesos malsukcesis repo branĉo versio
ŝanĝo ŝanĝojn ĝisdatigo testoj testo konfirmi konfirmas konfirmita
nuligi nulita prokrasto prokrastita disponibla libera okupata konekto
roboto agento mesaĝojn kodo programo programon
hieraŭ matene vespere nokte kun sen por ĉar tamen do jam ankoraŭ
ankaŭ denove preskaŭ ĝis post antaŭ dum sub super trans apud
kiu kion kie kiam kial kiom tiu tion tiun tio
gravas utilas eblus bonvolu korpekti ripari riparas
listo liston numero dato horaron horaron
progreso procento nivelo celo celon rezulto rezultojn
papero plumo libro libron vorto vortojn frazo gramatiko
viro virino infano amiko amikon samideano samideanojn
urbo domo pordo vojo akvo pano lakto kafejo
laboranton kolego kolegon estro ĉefo helpanto
demandon respondon dankon pardonon saluton
kompreni komprenas komprenis
utila ebla necesaa nepre verajn vera vera bonan bonan
""".split()

unknown = sorted({c for c in CANDS if not s.recognised(c, roots, words)})
print('UNKNOWN (%d):' % len(unknown))
for u in unknown:
    print(' ', u)
