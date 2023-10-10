/*
 * Copyright 2020 Regents of the University of Minnesota.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package edu.umn.biomedicus.concepts;

import edu.umn.biomedicus.common.pos.PartOfSpeech;
import edu.umn.nlpie.mtap.common.JsonObjectImpl;
import edu.umn.nlpie.mtap.model.*;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.MockitoSession;

import java.util.Arrays;
import java.util.Collections;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.when;

public class DictionaryConceptDetectorTest {
    private MockitoSession mockitoSession;

    @Mock
    ConceptDictionary conceptDictionary;

    @BeforeEach
    void setUp() {
        mockitoSession = Mockito.mockitoSession()
            .initMocks(this)
            .startMocking();
    }

    @AfterEach
    void tearDown() {
        mockitoSession.finishMocking();
    }

    @Test
    void testCovid19() {
        DictionaryConceptDetector conceptDetector = new DictionaryConceptDetector(conceptDictionary,
            null, 8);

        when(conceptDictionary.forPhrase("COVID-19"))
            .thenReturn(Collections.singletonList(new ConceptRow(new SUI("S1960864"),
                new CUI("C5203670"), new TUI("T047"), 2, "NOCODE")));
        when(conceptDictionary.forPhrase("COVID")).thenReturn(null);
        when(conceptDictionary.forLowercasePhrase("covid")).thenReturn(null);

        Event event = Event.newBuilder().eventID("1").build();
        Document document = event.createDocument("plaintext", "COVID-19");
        document.addLabels("sentences",
            Collections.singletonList(GenericLabel.createSpan(0, 8)));
        document.addLabels("pos_tags",
            Arrays.asList(GenericLabel.withSpan(0, 5).setProperty("tag", "NN").build(),
                GenericLabel.withSpan(5, 6).setProperty("tag", "HYPH").build(),
                GenericLabel.withSpan(6, 8).setProperty("tag", "CD").build()));
        document.addLabels("norm_forms",
            Arrays.asList(GenericLabel.withSpan(0, 5).setProperty("norm", "covid").build(),
                GenericLabel.withSpan(5, 6).setProperty("norm", "-").build(),
                GenericLabel.withSpan(6, 8).setProperty("norm", "19").build()));
        document.addLabels("acronyms", Collections.emptyList());
        conceptDetector.process(document, JsonObjectImpl.newBuilder().build(), JsonObjectImpl.newBuilder());
        document.getLabelIndices().get("umls_concepts");
    }

    @Test
    void longPhrase() {
        DictionaryConceptDetector conceptDetector = new DictionaryConceptDetector(conceptDictionary, null, 8);

        Event event = Event.newBuilder().eventID("1").build();
        Document document = event.createDocument("plaintext", "laceration of the extensor digiti minimi.");
        when(conceptDictionary.forPhrase("laceration")).thenReturn(null);
        when(conceptDictionary.forLowercasePhrase("laceration")).thenReturn(null);
        when(conceptDictionary.forPhrase("laceration of the extensor")).thenReturn(null);
        when(conceptDictionary.forLowercasePhrase("laceration of the extensor")).thenReturn(null);
        when(conceptDictionary.forPhrase("laceration of the extensor digiti")).thenReturn(null);
        when(conceptDictionary.forLowercasePhrase("laceration of the extensor digiti")).thenReturn(null);
        when(conceptDictionary.forPhrase("laceration of the extensor digiti minimi"))
            .thenReturn(Collections.singletonList(new ConceptRow(new SUI("S1234567"),
                new CUI("C1234567"), new TUI("T123"), 1, "NOCODE")));
        when(conceptDictionary.source(1)).thenReturn("test");
        document.addLabels("sentences",
            Collections.singletonList(
                GenericLabel.createSpan(0, 41)
            ));
        document.addLabels("pos_tags",
            Arrays.asList(
                GenericLabel.withSpan(0, 10).setProperty("tag", "NN").build(),
                GenericLabel.withSpan(11, 13).setProperty("tag", PartOfSpeech.IN.toString()).build(),
                GenericLabel.withSpan(14, 17).setProperty("tag", PartOfSpeech.DT.toString()).build(),
                GenericLabel.withSpan(18, 26).setProperty("tag", PartOfSpeech.NN.toString()).build(),
                GenericLabel.withSpan(27, 33).setProperty("tag", PartOfSpeech.NN.toString()).build(),
                GenericLabel.withSpan(34, 40).setProperty("tag", PartOfSpeech.NN.toString()).build(),
                GenericLabel.withSpan(40, 41).setProperty("tag", PartOfSpeech.SENTENCE_CLOSER_PUNCTUATION.toString()).build()
            ));
        document.addLabels("norm_forms",
            Arrays.asList(
                GenericLabel.withSpan(0, 10).setProperty("norm", "laceration").build(),
                GenericLabel.withSpan(11, 13).setProperty("norm", "of").build(),
                GenericLabel.withSpan(14, 17).setProperty("norm", "the").build(),
                GenericLabel.withSpan(18, 26).setProperty("norm", "extensor").build(),
                GenericLabel.withSpan(27, 33).setProperty("norm", "digiti").build(),
                GenericLabel.withSpan(34, 40).setProperty("norm", "minimi").build(),
                GenericLabel.withSpan(40, 41).setProperty("norm", ".").build()
            ));
        document.addLabels("acronyms", Collections.emptyList());
        conceptDetector.process(document, JsonObjectImpl.newBuilder().build(), JsonObjectImpl.newBuilder());
        LabelIndex<Label> umlsConcepts = document.getLabelIndex("umls_concepts");
        assertEquals(umlsConcepts.size(), 1);
    }
}
