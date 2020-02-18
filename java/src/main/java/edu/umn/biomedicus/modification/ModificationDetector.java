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

package edu.umn.biomedicus.modification;

import edu.umn.biomedicus.common.pos.PartOfSpeech;
import edu.umn.biomedicus.common.tuples.Pair;
import edu.umn.nlpie.mtap.common.JsonObject;
import edu.umn.nlpie.mtap.common.JsonObjectBuilder;
import edu.umn.nlpie.mtap.model.Document;
import edu.umn.nlpie.mtap.model.GenericLabel;
import edu.umn.nlpie.mtap.model.LabelIndex;
import edu.umn.nlpie.mtap.model.Labeler;
import edu.umn.nlpie.mtap.processing.*;
import org.jetbrains.annotations.NotNull;
import org.kohsuke.args4j.CmdLineException;
import org.kohsuke.args4j.CmdLineParser;

import java.io.IOException;
import java.util.List;
import java.util.stream.Collectors;

import static edu.umn.biomedicus.modification.ModificationType.*;

/**
 *
 */
@Processor(
    value = "biomedicus-modification",
    humanName = "BioMedICUS Modification Detector",
    description = "Detects Historical, Negated, and Uncertain modifications on umls terms",
    parameters = {
        @ParameterDescription(name = "terms_index", dataType = "str")
    },
    inputs = {
        @LabelIndexDescription(name = "sentences", reference = "biomedicus-sentences/sentences"),
        @LabelIndexDescription(name = "pos_tags", reference = "biomedicus-tnt-tagger/pos_tags"),
        @LabelIndexDescription(name = "umls_terms", reference = "biomedicus-concepts/umls_terms",
            nameFromParameter = "terms_index")
    },
    outputs = {
        @LabelIndexDescription(name = "negated", description = "Spans of negated terms."),
        @LabelIndexDescription(name = "uncertain", description = "Spans of terms that are uncertain."),
        @LabelIndexDescription(name = "historical", description = "Spans of terms that are historical.")
    }
)
public class ModificationDetector extends DocumentProcessor {

  private static final ContextCues CUES = ContextCues
      .builder()
      .addLeftPhrase(HISTORICAL, "History")
      .addLeftPhrase(HISTORICAL, "history")
      .addLeftPhrase(HISTORICAL, "Historical")
      .addLeftPhrase(HISTORICAL, "historical")
      .addLeftPhrase(HISTORICAL, "Histories")
      .addLeftPhrase(HISTORICAL, "histories")
      .addLeftPhrase(HISTORICAL, "Status", "Post")
      .addLeftPhrase(HISTORICAL, "Status", "post")
      .addLeftPhrase(HISTORICAL, "status", "post")
      .addLeftPhrase(HISTORICAL, "S/P")
      .addLeftPhrase(HISTORICAL, "s/p")
      .addLeftPhrase(HISTORICAL, "S-P")
      .addLeftPhrase(HISTORICAL, "s-p")
      .addLeftPhrase(HISTORICAL, "S.P.")
      .addLeftPhrase(HISTORICAL, "s.p.")
      .addLeftPhrase(HISTORICAL, "SP")
      .addLeftPhrase(HISTORICAL, "sp")
      .addRightPhrase(HISTORICAL, "History")
      .addRightPhrase(HISTORICAL, "history")
      .addLeftPhrase(NEGATED, "No")
      .addLeftPhrase(NEGATED, "no")
      .addLeftPhrase(NEGATED, "Deny")
      .addLeftPhrase(NEGATED, "deny")
      .addLeftPhrase(NEGATED, "Denies")
      .addLeftPhrase(NEGATED, "denies")
      .addLeftPhrase(NEGATED, "Denying")
      .addLeftPhrase(NEGATED, "denying")
      .addLeftPhrase(NEGATED, "Absent")
      .addLeftPhrase(NEGATED, "absent")
      .addLeftPhrase(NEGATED, "Negative")
      .addLeftPhrase(NEGATED, "negative")
      .addLeftPhrase(NEGATED, "Without")
      .addLeftPhrase(NEGATED, "without")
      .addLeftPhrase(NEGATED, "w/o")
      .addLeftPhrase(NEGATED, "W/O")
      .addLeftPhrase(NEGATED, "Never")
      .addLeftPhrase(NEGATED, "never")
      .addLeftPhrase(NEGATED, "Unremarkable")
      .addLeftPhrase(NEGATED, "unremarkable")
      .addLeftPhrase(NEGATED, "Un-remarkable")
      .addLeftPhrase(NEGATED, "un-remarkable")
      .addRightPhrase(NEGATED, "none")
      .addRightPhrase(NEGATED, "negative")
      .addRightPhrase(NEGATED, "absent")
      .addLeftPhrase(UNCERTAIN, "Possible")
      .addLeftPhrase(UNCERTAIN, "possible")
      .addLeftPhrase(UNCERTAIN, "Possibly")
      .addLeftPhrase(UNCERTAIN, "possibly")
      .addLeftPhrase(UNCERTAIN, "Probable")
      .addLeftPhrase(UNCERTAIN, "probable")
      .addLeftPhrase(UNCERTAIN, "Probably")
      .addLeftPhrase(UNCERTAIN, "probably")
      .addLeftPhrase(UNCERTAIN, "Might")
      .addLeftPhrase(UNCERTAIN, "might")
      .addLeftPhrase(UNCERTAIN, "likely")
      .addLeftPhrase(UNCERTAIN, "Likely")
      .addLeftPhrase(UNCERTAIN, "am", "not", "sure")
      .addLeftPhrase(UNCERTAIN, "Am", "not", "sure")
      .addLeftPhrase(UNCERTAIN, "Not", "sure")
      .addLeftPhrase(UNCERTAIN, "not", "sure")
      .addLeftPhrase(UNCERTAIN, "Differential")
      .addLeftPhrase(UNCERTAIN, "differential")
      .addLeftPhrase(UNCERTAIN, "Uncertain")
      .addLeftPhrase(UNCERTAIN, "uncertain")
      .addLeftPhrase(UNCERTAIN, "chance")
      .addLeftPhrase(UNCERTAIN, "Chance")
      .addRightPhrase(UNCERTAIN, "likely")
      .addRightPhrase(UNCERTAIN, "probable")
      .addRightPhrase(UNCERTAIN, "unlikely")
      .addRightPhrase(UNCERTAIN, "possible")
      .addRightPhrase(UNCERTAIN, "uncertain")
      .addScopeDelimitingPos(PartOfSpeech.WDT)
      .addScopeDelimitingPos(PartOfSpeech.PRP)
      .addScopeDelimitingPos(PartOfSpeech.VBZ)
      .addScopeDelimitingWord("but")
      .addScopeDelimitingWord("however")
      .addScopeDelimitingWord("therefore")
      .addScopeDelimitingWord("otherwise")
      .addScopeDelimitingWord("except")
      .addScopeDelimitingWord(";")
      .addScopeDelimitingWord(":")
      .build();

  public static void runModificationDetector(ProcessorServerOptions options) throws IOException, InterruptedException {
    ModificationDetector detector = new ModificationDetector();
    ProcessorServer server = ProcessorServerBuilder.forProcessor(detector, options).build();
    server.start();
    server.blockUntilShutdown();
  }

  public static void main(String[] args) {
    ProcessorServerOptions options = new ProcessorServerOptions();
    CmdLineParser parser = new CmdLineParser(options);
    try {
      parser.parseArgument(args);
      runModificationDetector(options);
    } catch (CmdLineException e) {
      ProcessorServerOptions.printHelp(parser, ModificationDetector.class, e, null);
    } catch (InterruptedException | IOException e) {
      e.printStackTrace();
    }
  }

  @Override
  protected void process(@NotNull Document document, @NotNull JsonObject params, @NotNull JsonObjectBuilder result) {
    LabelIndex<GenericLabel> sentences = document.getLabelIndex("sentences");
    LabelIndex<GenericLabel> posTags = document.getLabelIndex("pos_tags");
    LabelIndex<GenericLabel> umlsTerms = document.getLabelIndex("umls_terms");

    try (
        Labeler<GenericLabel> uncertainLabeler = document.getLabeler("uncertain");
        Labeler<GenericLabel> historicalLabeler = document.getLabeler("historical");
        Labeler<GenericLabel> negatedLabeler = document.getLabeler("negated");
        Labeler<GenericLabel> cueLabeler = document.getLabeler("modification_cue");
    ) {
      for (GenericLabel termLabel : umlsTerms) {
        GenericLabel sentenceLabel = sentences.covering(termLabel).first();

        if (sentenceLabel == null) {
          throw new RuntimeException("Term outside of a sentence.");
        }

        LabelIndex<GenericLabel> sentenceTags = posTags.inside(sentenceLabel);
        List<GenericLabel> contextList = sentenceTags.backwardFrom(termLabel).asList();

        Pair<ModificationType, List<GenericLabel>> searchResult = CUES.searchLeft(contextList);

        if (searchResult != null) {
          List<GenericLabel> cues = searchResult.second().stream().map(span -> {
            GenericLabel cue = GenericLabel.withSpan(span).build();
            cueLabeler.add(cue);
            return cue;
          }).collect(Collectors.toList());
          switch (searchResult.first()) {
            case HISTORICAL:
              historicalLabeler.add(GenericLabel.withSpan(termLabel).build());
              break;
            case NEGATED:
              negatedLabeler.add(GenericLabel.withSpan(termLabel).build());
              break;
            case UNCERTAIN:
              uncertainLabeler.add(GenericLabel.withSpan(termLabel).build());
              break;
            default:
              throw new IllegalStateException();
          }
          continue;
        }

        contextList = sentenceTags.forwardFrom(termLabel).asList();

        searchResult = CUES.searchRight(contextList);
        if (searchResult != null) {
          List<GenericLabel> cues = searchResult.second().stream().map(span -> {
            GenericLabel cue = GenericLabel.withSpan(span).build();
            cueLabeler.add(cue);
            return cue;
          }).collect(Collectors.toList());
          switch (searchResult.first()) {
            case HISTORICAL:
              historicalLabeler.add(GenericLabel.withSpan(termLabel).build());
              break;
            case NEGATED:
              negatedLabeler.add(GenericLabel.withSpan(termLabel).build());
              break;
            case UNCERTAIN:
              uncertainLabeler.add(GenericLabel.withSpan(termLabel).build());
              break;
            default:
              throw new IllegalStateException();
          }
        }
      }
    }
  }
}
