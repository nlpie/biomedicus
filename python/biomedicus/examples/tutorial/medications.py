from mtap import DocumentProcessor, run_processor


class MedicationsProcessor(DocumentProcessor):
    def process_document(self, document, params):
        sentences = document.labels['sentences']
        umls_concepts = document.labels['umls_concepts']
        with document.get_labeler('medication_sentences') as MedicationSentence:
            for sentence in sentences:
                medication_concepts = []
                for concept in umls_concepts.inside(sentence):
                    if concept.tui == 'T121':
                        medication_concepts.append(concept)
                if len(medication_concepts) > 0:
                    MedicationSentence(sentence.start_index, sentence.end_index,
                                       concepts=medication_concepts)


if __name__ == '__main__':
    run_processor(MedicationsProcessor())
