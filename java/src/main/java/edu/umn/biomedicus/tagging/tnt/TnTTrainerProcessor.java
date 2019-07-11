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
import edu.umn.nlpnewt.common.JsonObject;
import edu.umn.nlpnewt.common.JsonObjectBuilder;
import edu.umn.nlpnewt.model.Document;
import edu.umn.nlpnewt.model.GenericLabel;
import edu.umn.nlpnewt.model.LabelIndex;
import edu.umn.nlpnewt.processing.DocumentProcessor;
import org.jetbrains.annotations.NotNull;

import java.io.IOException;
import java.nio.file.Path;
import java.util.List;

/**
 * Trains the TnT model using the tagged parts of speech in all documents.
 *
 * @author Ben Knoll
 * @since 1.7.0
 */
public class TnTTrainerProcessor extends DocumentProcessor {
  private final TntModelTrainer tntModelTrainer;

  private final Path outputDir;

  TnTTrainerProcessor(@NotNull Path outputDir,
                      @NotNull DataStoreFactory dataStoreFactory) {
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
  protected void process(@NotNull Document document, @NotNull JsonObject params, @NotNull JsonObjectBuilder result) {
    LabelIndex<GenericLabel> sentences = document.getLabelIndex("sentences");
    LabelIndex<GenericLabel> partsOfSpeech = document.getLabelIndex("pos_tags");

    for (GenericLabel sentence : sentences) {
      List<GenericLabel> sentencesPos = partsOfSpeech.inside(sentence).asList();
      tntModelTrainer.addSentence(document.getText(), sentencesPos);
    }
  }

  void done() throws IOException {
    tntModelTrainer.createModel().write(outputDir);
  }
}
