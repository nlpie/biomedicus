/*
 * Copyright 2019 Regents of the University of Minnesota.
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

package edu.umn.biomedicus.utilities;

import edu.umn.biomedicus.common.pos.PartOfSpeech;
import edu.umn.biomedicus.common.pos.PartsOfSpeech;
import edu.umn.biomedicus.utilities.PtbReader.Node;
import edu.umn.nlpie.mtap.common.JsonObject;
import edu.umn.nlpie.mtap.common.JsonObjectBuilder;
import edu.umn.nlpie.mtap.model.Document;
import edu.umn.nlpie.mtap.model.Event;
import edu.umn.nlpie.mtap.model.GenericLabel;
import edu.umn.nlpie.mtap.processing.*;
import org.jetbrains.annotations.NotNull;
import org.kohsuke.args4j.CmdLineException;
import org.kohsuke.args4j.CmdLineParser;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

@Processor("ptb-reader")
public class PtbReaderProcessor extends EventProcessor {
  @Override
  public void process(@NotNull Event event,
                      @NotNull JsonObject params,
                      @NotNull JsonObjectBuilder<?, ?> result) {
    String sourceDocumentName = params.getStringValue("source_document_name");
    if (sourceDocumentName == null) {
      sourceDocumentName = "source";
    }
    String targetDocumentName = params.getStringValue("target_document_name");
    if (targetDocumentName == null) {
      targetDocumentName = "plaintext";
    }

    List<GenericLabel> sentences = new ArrayList<>();
    List<GenericLabel> posTags = new ArrayList<>();
    StringBuilder documentBuilder = new StringBuilder();
    PtbReader reader = PtbReader.create(event.getDocuments().get(sourceDocumentName).getText());
    try {
      Node node;
      while ((node = reader.nextNode()) != null) {
        int sentBegin = documentBuilder.length();
        Iterator<Node> leafIterator = node.leafIterator();
        while (leafIterator.hasNext()) {
          Node leaf = leafIterator.next();
          if ("-NONE-".equals(leaf.getLabel())) {
            continue;
          }

          String word = leaf.getWord();
          if (word == null) {
            continue;
          }

          int begin = documentBuilder.length();
          int end = begin + word.length();
          documentBuilder.append(word).append(' ');
          String label = leaf.getLabel();
          PartOfSpeech partOfSpeech = PartsOfSpeech.forTagWithFallback(label);
          if (partOfSpeech == null) {
            partOfSpeech = PartOfSpeech.XX;
          }
          posTags.add(GenericLabel.withSpan(begin, end)
              .setProperty("tag", partOfSpeech.toString())
              .build());

        }
        int sentEnd = documentBuilder.length();
        sentences.add(GenericLabel.createSpan(sentBegin, sentEnd));
      }
    } catch (IOException e) {
      throw new IllegalStateException(e);
    }

    Document target = event.createDocument(targetDocumentName, documentBuilder.toString());
    String sentencesIndex = (String) params.getOrDefault("sentences_index", "sentences");
    target.addLabels(sentencesIndex, true, sentences);
    String posTagsIndex = (String) params.getOrDefault("pos_tags_index", "pos_tags");
    target.addLabels(posTagsIndex, true, posTags);
  }

  public static void main(String[] args) {
    ProcessorServer.Builder options = new ProcessorServer.Builder();
    CmdLineParser parser = new CmdLineParser(options);
    try {
      parser.parseArgument(args);
      ProcessorServer server = options.build(new PtbReaderProcessor());
      server.start();
      server.blockUntilShutdown();
    } catch (CmdLineException e) {
      ProcessorServer.Builder.printHelp(parser, PtbReaderProcessor.class, e, null);
    } catch (InterruptedException | IOException e) {
      e.printStackTrace();
    }
  }
}
