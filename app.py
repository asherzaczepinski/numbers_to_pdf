import os
from music21 import (
    stream, note, key, scale, clef, instrument,
    environment, expressions, duration, layout
)
from PyPDF2 import PdfMerger
from flask import Flask, request, send_file

# ------------------------------------------------------------------------
# Configuration: Point music21 to MuseScore 3 (adjust if necessary)
# ------------------------------------------------------------------------
environment.set('musicxmlPath', '/Applications/MuseScore 3.app/Contents/MacOS/mscore')
environment.set('musescoreDirectPNGPath', '/Applications/MuseScore 3.app/Contents/MacOS/mscore')

# ------------------------------------------------------------------------
# Enharmonic mapping: name -> (newName, octaveAdjustment)
# ------------------------------------------------------------------------
ENHARM_MAP = {
    "E#": ("F", 0),
    "B#": ("C", +1),
    "Cb": ("B", -1),
    "Fb": ("E", 0),
}

# ------------------------------------------------------------------------
# Easiest playable note (defaults to "C4" if not found)
# ------------------------------------------------------------------------
EASIEST_NOTE_MAP = {
    "Piano": "C4",
    "Alto Saxophone": "D4",
    "Violin": "G3",
    "Flute": "G4",
    "Clarinet": "E4",
    # Add more instruments and their easy notes as desired
}

def fix_enharmonic_spelling(n):
    if not n.pitch:
        return
    original_name = n.pitch.name
    if original_name in ENHARM_MAP:
        new_name, octave_adjust = ENHARM_MAP[original_name]
        n.pitch.name = new_name
        n.pitch.octave += octave_adjust
    if n.pitch.accidental is not None:
        n.pitch.accidental.displayStatus = True
        n.pitch.accidental.displayType = 'normal'

def determine_clef_and_octave(instrument_name, part='right'):
    if instrument_name == "Piano":
        return {"right": ("TrebleClef", 4), "left": ("BassClef", 2)}
    instrument_map = {
        "Violin":       ("TrebleClef", 3),
        "Viola":        ("AltoClef",   3),
        "Cello":        ("BassClef",   2),
        "Double Bass":  ("BassClef",   1),
        "Guitar":       ("TrebleClef", 3),
        "Harp":         ("TrebleClef", 3),
        "Alto Saxophone":   ("TrebleClef", 4),
        "Bass Clarinet":    ("TrebleClef", 2),
        "Bassoon":          ("BassClef",   2),
        "Clarinet":         ("TrebleClef", 3),
        "English Horn":     ("TrebleClef", 4),
        "Flute":            ("TrebleClef", 4),
        "Oboe":             ("TrebleClef", 4),
        "Piccolo":          ("TrebleClef", 5),
        "Tenor Saxophone":  ("TrebleClef", 3),
        "Trumpet":          ("TrebleClef", 4),
        "Euphonium":    ("BassClef", 2),
        "French Horn":  ("TrebleClef", 3),
        "Trombone":     ("BassClef", 2),
        "Tuba":         ("BassClef", 1),
        "Marimba":      ("TrebleClef", 3),
        "Timpani":      ("BassClef",   3),
        "Vibraphone":   ("TrebleClef", 3),
        "Xylophone":    ("TrebleClef", 4),
        "Electric Piano": ("TrebleClef", 4),
        "Organ":          ("TrebleClef", 4),
        "Voice":        ("TrebleClef", 4),
    }
    unpitched_percussion = {"Bass Drum", "Cymbals", "Snare Drum", "Triangle", "Tambourine"}
    if instrument_name in unpitched_percussion:
        return ("PercussionClef", 4)
    return instrument_map.get(instrument_name, ("TrebleClef", 4))

def create_scale_measures(title_text, scale_object, octave_start, num_octaves):
    measures_stream = stream.Stream()
    pitches_up = scale_object.getPitches(f"{scale_object.tonic.name}{octave_start}",
                                        f"{scale_object.tonic.name}{octave_start + num_octaves}")
    pitches_down = list(reversed(pitches_up[:-1]))
    all_pitches = pitches_up + pitches_down
    notes_per_measure = 7
    current_measure = stream.Measure()
    note_counter = 0

    for i, p in enumerate(all_pitches):
        if i == len(all_pitches) - 1:
            if current_measure.notes:
                measures_stream.append(current_measure)
            m_whole = stream.Measure()
            if i == 0:
                txt = expressions.TextExpression(title_text)
                txt.placement = 'above'
                m_whole.insert(0, txt)
            n = note.Note(p)
            n.duration = duration.Duration('whole')
            fix_enharmonic_spelling(n)
            m_whole.append(n)
            measures_stream.append(m_whole)
            break

        pos_in_measure = note_counter % notes_per_measure
        if pos_in_measure == 0:
            if current_measure.notes:
                measures_stream.append(current_measure)
            current_measure = stream.Measure()
            if i == 0:
                txt = expressions.TextExpression(title_text)
                txt.placement = 'above'
                current_measure.insert(0, txt)
            n = note.Note(p)
            n.duration = duration.Duration('quarter')
            fix_enharmonic_spelling(n)
            current_measure.append(n)
        else:
            n = note.Note(p)
            n.duration = duration.Duration('eighth')
            fix_enharmonic_spelling(n)
            current_measure.append(n)
        note_counter += 1

    return measures_stream

def create_arpeggio_measures(title_text, scale_object, octave_start, num_octaves):
    measures_stream = stream.Stream()
    scale_pitches = scale_object.getPitches(f"{scale_object.tonic.name}{octave_start}",
                                            f"{scale_object.tonic.name}{octave_start + num_octaves}")
    arpeggio_up = []
    for o in range(num_octaves):
        base_idx = 7 * o
        try:
            root = scale_pitches[base_idx + 0]
            third = scale_pitches[base_idx + 2]
            fifth = scale_pitches[base_idx + 4]
            if o < num_octaves - 1:
                arpeggio_up.extend([root, third, fifth])
            else:
                octave_tone = scale_pitches[base_idx + 7]
                arpeggio_up.extend([root, third, fifth, octave_tone])
        except IndexError:
            pass
    arpeggio_down = list(reversed(arpeggio_up[:-1])) if len(arpeggio_up) > 1 else []
    all_arpeggio_pitches = arpeggio_up + arpeggio_down
    notes_per_measure = 8
    current_measure = stream.Measure()
    note_counter = 0

    for i, p in enumerate(all_arpeggio_pitches):
        if i == len(all_arpeggio_pitches) - 1:
            if current_measure.notes:
                measures_stream.append(current_measure)
            m_whole = stream.Measure()
            if i == 0:
                txt = expressions.TextExpression(title_text)
                txt.placement = 'above'
                m_whole.insert(0, txt)
            n = note.Note(p)
            n.duration = duration.Duration('whole')
            fix_enharmonic_spelling(n)
            m_whole.append(n)
            measures_stream.append(m_whole)
            break

        pos_in_measure = note_counter % notes_per_measure
        if pos_in_measure == 0:
            if current_measure.notes:
                measures_stream.append(current_measure)
            current_measure = stream.Measure()
            if i == 0:
                txt = expressions.TextExpression(title_text)
                txt.placement = 'above'
                current_measure.insert(0, txt)
        n = note.Note(p)
        n.duration = duration.Duration('eighth')
        fix_enharmonic_spelling(n)
        current_measure.append(n)
        note_counter += 1

    return measures_stream

def create_part_for_single_key_scales_arpeggios(key_signature, num_octaves, instrument_name):
    part = stream.Part()
    instr_obj = instrument.fromString(instrument_name)
    part.insert(0, instr_obj)
    part.insert(0, layout.SystemLayout(isNew=True))
    major_key_obj = key.Key(key_signature, 'major')
    major_scale_obj = scale.MajorScale(key_signature)
    clef_octave = determine_clef_and_octave(instrument_name)
    if isinstance(clef_octave, dict):
        selected_clef, octave_start = clef_octave.get('right', ("TrebleClef", 4))
    else:
        selected_clef, octave_start = clef_octave

    scale_measures = create_scale_measures(
        title_text=f"{key_signature} Major Scale",
        scale_object=major_scale_obj,
        octave_start=octave_start,
        num_octaves=num_octaves
    )
    if scale_measures:
        first_m = scale_measures[0]
        first_m.insert(0, getattr(clef, selected_clef)())
        first_m.insert(0, major_key_obj)
        for m in scale_measures:
            part.append(m)
    part.append(layout.SystemLayout(isNew=True))

    arpeggio_measures = create_arpeggio_measures(
        title_text=f"{key_signature} Major Arpeggio",
        scale_object=major_scale_obj,
        octave_start=octave_start,
        num_octaves=num_octaves
    )
    if arpeggio_measures:
        first_arp = arpeggio_measures[0]
        first_arp.insert(0, major_key_obj)
        for m in arpeggio_measures:
            part.append(m)
    return part

def create_custom_rhythm_part(title_text, custom_rhythm, instrument_name):
    part = stream.Part()
    instr_obj = instrument.fromString(instrument_name)
    part.insert(0, instr_obj)
    part.insert(0, layout.SystemLayout(isNew=True))
    easiest_note = EASIEST_NOTE_MAP.get(instrument_name, "C4")
    measures_stream = stream.Stream()

    for measure_index, measure_durations in enumerate(custom_rhythm):
        current_measure = stream.Measure()
        if measure_index == 0:
            txt = expressions.TextExpression(title_text)
            txt.placement = 'above'
            current_measure.insert(0, txt)
        for val in measure_durations:
            n = note.Note(easiest_note)
            fix_enharmonic_spelling(n)
            n.duration = duration.Duration(val * 4)
            current_measure.append(n)
        measures_stream.append(current_measure)

    for m in measures_stream:
        part.append(m)
    return part

def generate_scales_arpeggios_pdf(output_folder, keys, num_octaves, instrument_name):
    os.makedirs(output_folder, exist_ok=True)
    scales_arpeggios_score = stream.Score()

    for key_sig in keys:
        part_for_key = create_part_for_single_key_scales_arpeggios(
            key_signature=key_sig,
            num_octaves=num_octaves,
            instrument_name=instrument_name
        )
        scales_arpeggios_score.append(part_for_key)

    scales_pdf = os.path.join(output_folder, "ScalesAndArpeggios.pdf")
    scales_arpeggios_score.write('musicxml.pdf', fp=scales_pdf)
    return scales_pdf

def generate_custom_rhythm_pdf(output_folder, custom_rhythm_example, title, instrument_name):
    os.makedirs(output_folder, exist_ok=True)
    custom_rhythm_score = stream.Score()
    custom_rhythm_part = create_custom_rhythm_part(
        title_text=title,
        custom_rhythm=custom_rhythm_example,
        instrument_name=instrument_name
    )
    custom_rhythm_score.append(custom_rhythm_part)
    custom_pdf = os.path.join(output_folder, "CustomRhythm.pdf")
    custom_rhythm_score.write('musicxml.pdf', fp=custom_pdf)
    return custom_pdf

def merge_pdfs(pdf_list, output_path):
    merger = PdfMerger()
    for pdf in pdf_list:
        merger.append(pdf)
    merger.write(output_path)
    merger.close()
    return output_path

# Initialize Flask application
app = Flask(__name__)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()

    # Extract parameters from the request JSON
    output_folder = data.get('output_folder', './output')
    multiple_keys = data.get('keys', ["F#", "C", "G", "A", "B", "D", "E", "Eb"])
    num_octaves = data.get('num_octaves', 1)
    instrument_name = data.get('instrument_name', "Alto Saxophone")
    custom_rhythm = data.get('custom_rhythm', [[1], [0.5, 0.5]])
    custom_line_title = data.get('custom_line_title', "My Custom Rhythm (Standard Staff)")

    # Generate PDFs
    scales_pdf = generate_scales_arpeggios_pdf(output_folder, multiple_keys, num_octaves, instrument_name)
    custom_pdf = generate_custom_rhythm_pdf(output_folder, custom_rhythm, custom_line_title, instrument_name)

    # Merge PDFs into one
    allinone_pdf = os.path.join(output_folder, "AllInOne.pdf")
    merge_pdfs([scales_pdf, custom_pdf], allinone_pdf)

    # Return the combined PDF directly as a response
    return send_file(allinone_pdf, mimetype='application/pdf', as_attachment=True, download_name='AllInOne.pdf')

if __name__ == '__main__':
    # For Google Cloud Run, bind to 0.0.0.0 and get the port from environment variable
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
