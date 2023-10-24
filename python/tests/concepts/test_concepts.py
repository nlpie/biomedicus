from importlib_resources import files
from mtap import Pipeline, RemoteProcessor, events_client
from mtap.serialization import JsonSerializer


def test_duplicate_concepts(events_service, concepts_service):
    pipeline = Pipeline(
        RemoteProcessor(name='biomedicus-concepts', address=concepts_service),
        events_address=events_service
    )
    with events_client(events_service) as client:
        with files().joinpath('concepts_test.json').open('r') as f:
            event = JsonSerializer.file_to_event(f, client)
        with event:
            doc = event.documents['plaintext']
            pipeline.run(doc)
            text = doc.text
            concepts = doc.labels['umls_concepts']

            # Negative for chest pain
            start = text.find("for chest pain")
            start2 = start + 4
            end = start + 14
            first = concepts.inside(start, end)
            second = concepts.inside(start2, end)
            assert len(second) > 0
            assert len(first) == len(second)

            # Pt states woke...
            start = text.find("with chest pain")
            start2 = start + 5
            end = start + 15
            first = concepts.inside(start, end)
            second = concepts.inside(start2, end)
            assert len(second) > 0
            assert len(first) == len(second)

            start = text.find("and throat tightness")
            start2 = start + 4
            end = start + 20
            first = concepts.inside(start, end)
            second = concepts.inside(start2, end)
            assert len(second) > 0
            assert len(first) == len(second)

            # Negative for abdominal...
            start = text.find("for abdominal pain")
            start2 = start + 4
            end = start + 18
            first = concepts.inside(start, end)
            second = concepts.inside(start2, end)
            assert len(second) > 0
            assert len(first) == len(second)

            # sensory aura “warm feeling in her trunk” in the past
            start = text.find("“warm feeling")
            start2 = start + 1
            end = start + 13
            first = concepts.inside(start, end)
            second = concepts.inside(start2, end)
            assert len(second) > 0
            assert len(first) == len(second)

            # Author Type: Medical Assistant
            start = text.find(": Medical Assistant")
            start2 = start + 2
            end = start + 19
            first = concepts.inside(start, end)
            second = concepts.inside(start2, end)
            assert len(second) > 0
            assert len(first) == len(second)

            # Smith, Jane M, RN (Registered Nurse)
            start = text.find(", RN (Registered Nurse)")
            start2 = start + 2
            end = start + 23
            first = concepts.inside(start, end)
            second = concepts.inside(start2, end)
            assert len(second) > 0
            assert len(first) == len(second)

            start = text.find("(Registered Nurse)")
            start2 = start + 1
            end = start + 18
            first = concepts.inside(start, end)
            second = concepts.inside(start2, end)
            assert len(second) > 0
            assert len(first) == len(second)

            # Mild scoliosis, Bilateral R>L SI joint tenderness;
            start = text.find("Mild scoliosis,")
            end1 = start + 14
            end2 = start + 15
            first = concepts.inside(start, end1)
            second = concepts.inside(start, end2)
            assert len(first) > 0
            assert len(first) == len(second)

            # She was seen 3/3/23 in WIC and diagnosed with PCN allergy.
            start = text.find("PCN allergy.")
            end1 = start + 11
            end2 = start + 12
            first = concepts.inside(start, end1)
            second = concepts.inside(start, end2)
            assert len(first) > 0
            assert len(first) == len(second)

            # No signif signs, symptoms or concerns.
            start = text.find("signs, symptoms or")
            end1 = start + 15
            end2 = start + 18
            first = concepts.inside(start, end1)
            second = concepts.inside(start, end2)
            assert len(first) > 0
            assert len(first) == len(second)

            # Abdomen and pelvis:
            start = text.find("Abdomen and")
            end1 = start + 7
            end2 = start + 11
            first = concepts.inside(start, end1)
            second = concepts.inside(start, end2)
            assert len(first) > 0
            assert len(first) == len(second)
