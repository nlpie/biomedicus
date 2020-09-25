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

import edu.umn.biomedicus.normalization.NormalizerModel;
import edu.umn.nlpie.mtap.common.JsonObject;
import edu.umn.nlpie.mtap.common.JsonObjectImpl;
import edu.umn.nlpie.mtap.model.Document;
import edu.umn.nlpie.mtap.model.Event;
import edu.umn.nlpie.mtap.model.GenericLabel;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;

import static org.mockito.Mockito.when;

public class DictionaryConceptDetectorTest {

  @Mock
  ConceptDictionary conceptDictionary;

  @BeforeEach
  void setUp() {
    MockitoAnnotations.initMocks(this);
  }

  @Test
  void testCovid19() {
    DictionaryConceptDetector conceptDetector = new DictionaryConceptDetector(conceptDictionary,
        null);

    when(conceptDictionary.forPhrase("COVID-19"))
        .thenReturn(Collections.singletonList(new ConceptRow(new SUI("S1960864"),
            new CUI("C5203670"), new TUI("T047"), 2, "NOCODE")));
    when(conceptDictionary.forPhrase("COVID-")).thenReturn(null);
    when(conceptDictionary.forLowercasePhrase("covid-")).thenReturn(null);
    when(conceptDictionary.forPhrase("COVID")).thenReturn(null);
    when(conceptDictionary.forLowercasePhrase("covid")).thenReturn(null);
    when(conceptDictionary.forNorms("covid")).thenReturn(null);
    when(conceptDictionary.forNorms("19 covid")).thenReturn(
        Collections.singletonList(new ConceptRow(new SUI("S1960864"),
            new CUI("C5203670"), new TUI("T047"), 2, "NOCODE")));

    Event event = Event.newBuilder().eventID("1").build();
    Document document = event.createDocument("plaintext", "COVID-19");
    document.addLabels("sentences",
        Collections.singletonList(GenericLabel.createSpan(0, 8)));
    document.addLabels("pos_tags",
        Arrays.asList(GenericLabel.withSpan(0, 5).setProperty("tag", "NN").build(),
            GenericLabel.withSpan(5, 6).setProperty("tag", "HYPH").build(),
            GenericLabel.withSpan(6, 8).setProperty("tag", "#").build()));
    document.addLabels("norm_forms",
        Arrays.asList(GenericLabel.withSpan(0, 5).setProperty("norm", "covid").build(),
            GenericLabel.withSpan(5, 6).setProperty("norm", "-").build(),
            GenericLabel.withSpan(6, 8).setProperty("norm", "19").build()));
    document.addLabels("acronyms", Collections.emptyList());
    conceptDetector.process(document, JsonObjectImpl.newBuilder().build(), JsonObjectImpl.newBuilder());
    document.getLabelIndices().get("umls_concepts");
  }
}
