/*
 * Copyright (c) 2018 Regents of the University of Minnesota.
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

package edu.umn.biomedicus.tagging.tnt;

import edu.umn.nlpnewt.*;
import org.jetbrains.annotations.NotNull;
import sun.net.www.content.text.Generic;

import java.nio.file.Path;
import java.util.List;

/**
 * Trains the TnT model using the tagged parts of speech in all documents.
 *
 * @author Ben Knoll
 * @since 1.7.0
 */
public class TnTTrainerProcessor extends EventProcessor {

  private final String viewName;

  private final TntModelTrainer tntModelTrainer;

  private final Path outputDir;

  TnTTrainerProcessor(@NotNull String viewName,
                      @NotNull Path outputDir,
                      @NotNull DataStoreFactory dataStoreFactory) {
    this.viewName = viewName;

    dataStoreFactory.setDbPath(outputDir.resolve("words/"));

    tntModelTrainer = TntModelTrainer.builder()
        .useMslSuffixModel(false)
        .maxSuffixLength(5)
        .maxWordFrequency(20)
        .restrictToOpenClass(false)
        .useCapitalization(true)
        .dataStoreFactory(dataStoreFactory)
        .build();

    this.outputDir = outputDir;
  }

  @Override
  public void process(@NotNull Event event,
                      @NotNull JsonObject params,
                      @NotNull JsonObjectBuilder result) {
    Document view = event.getDocuments().get(viewName);

    if (view == null) {
      throw new RuntimeException("View was null: " + viewName);
    }

    LabelIndex<GenericLabel> sentences = view.getLabelIndex("sentences");
    LabelIndex<GenericLabel> partsOfSpeech = view.getLabelIndex("pos_tags");

    for (GenericLabel sentence : sentences) {
      List<GenericLabel> sentencesPos = partsOfSpeech.inside(sentence).asList();
      tntModelTrainer.addSentence(sentenceTokens, sentencesPos);
    }
  }
}
