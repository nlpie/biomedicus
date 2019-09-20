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

package edu.umn.biomedicus.concepts;

import edu.umn.biomedicus.common.config.Config;
import edu.umn.biomedicus.common.data.DataFiles;
import edu.umn.biomedicus.common.pos.PartOfSpeech;
import edu.umn.biomedicus.common.pos.PartsOfSpeech;
import edu.umn.biomedicus.common.tokenization.WhitespaceTokenizer;
import edu.umn.nlpnewt.common.JsonObject;
import edu.umn.nlpnewt.common.JsonObjectBuilder;
import edu.umn.nlpnewt.model.*;
import edu.umn.nlpnewt.processing.*;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.kohsuke.args4j.CmdLineException;
import org.kohsuke.args4j.CmdLineParser;
import org.kohsuke.args4j.Option;
import org.kohsuke.args4j.spi.ExplicitBooleanOptionHandler;
import org.rocksdb.RocksDBException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.file.Path;
import java.util.*;

import static edu.umn.biomedicus.common.pos.PartOfSpeech.*;

/**
 * Uses a {@link ConceptDictionary} to recognize concepts in text. First, it will try to find direct
 * matches against all in-order sublists of tokens in a sentence. Then it will perform syntactic
 * permutations on any prepositional phrases in those sublists.
 *
 * @author Ben Knoll
 * @author Serguei Pakhomov
 * @since 1.0.0
 */
@Processor(value = "biomedicus-concepts",
    description = "Labels UMLS Concepts",
    inputs = {
        @LabelIndexDescription(name = "sentences"),
        @LabelIndexDescription(name = "pos_tags",
            description = "Labeled part of speech tags on tokens.",
            properties = {
                @PropertyDescription(name = "tag", dataType = "str",
                    description = "The penn-treebank tag for the token.")
            }),
        @LabelIndexDescription(name = "norm_forms",
            description = "The labeled normalized form of a word per token.",
            properties = {
                @PropertyDescription(name = "norm", dataType = "str",
                    description = "The normal form of the word.")
            }),
        @LabelIndexDescription(name = "acronyms",
            description = "The highest scoring acronym disambiguation for an acronym.",
            properties = {
                @PropertyDescription(name = "score", dataType = "float",
                    description = "The acronym's score."),
                @PropertyDescription(name = "expansion", dataType = "str",
                    description = "The acronym's expansion.")
            }
        )
    },
    outputs = {
        @LabelIndexDescription(name = "concepts",
            description = "The UMLS concepts that appear in the text.",
            properties = {
                @PropertyDescription(name = "sui",
                    description = "The UMLS Source Unique Identifier for the concept.",
                    dataType = "str"),
                @PropertyDescription(name = "cui",
                    description = "The UMLS Concept Unique Identifier",
                    dataType = "str"),
                @PropertyDescription(name = "tui",
                    description = "The UMLS Type Unique Identifier",
                    dataType = "str"),
                @PropertyDescription(name = "source",
                    description = "The UMLS source dictionary the concept originated from",
                    dataType = "str"),
                @PropertyDescription(name = "score",
                    description = "A score for the concept, direct phrase matches are highest, lowest are the normalized bag of words matches.",
                    dataType = "float")
            }),
        @LabelIndexDescription(name = "terms",
            description = "Text that is covered by one or more concepts.")
    }
)
class DictionaryConceptDetector extends DocumentProcessor {

  private static final Logger LOGGER = LoggerFactory.getLogger(DictionaryConceptDetector.class);

  private static final Set<PartOfSpeech> TRIVIAL_POS = buildTrivialPos();

  private static final int SPAN_SIZE = 5;

  private final ConceptDictionary conceptDictionary;

  DictionaryConceptDetector(ConceptDictionary conceptDictionary) {this.conceptDictionary = conceptDictionary;}

  private static Set<PartOfSpeech> buildTrivialPos() {
    Set<PartOfSpeech> builder = new HashSet<>();
    Collections.addAll(builder,
        DT,
        CD,
        WDT,
        TO,
        CC,
        PRP,
        PRP$,
        MD,
        EX,
        IN,
        XX);

    Set<PartOfSpeech> punctuationClass = PartsOfSpeech.getPunctuationClass();
    builder.addAll(punctuationClass);
    return Collections.unmodifiableSet(builder);
  }

  public static @NotNull DictionaryConceptDetector createConceptDetector(
      @NotNull ConceptsOptions conceptsOptions
  ) throws IOException, RocksDBException {
    Config config = Config.loadFromDefaultLocations();
    DataFiles dataFiles = new DataFiles();
    Path dbPath = conceptsOptions.getDbPath();
    if (dbPath == null) {
      dbPath = dataFiles.getDataFile(config.getStringValue("concepts.db"));
    }
    Boolean inMemory = conceptsOptions.getInMemory();
    if (inMemory == null) {
      inMemory = config.getBooleanValue("concepts.inMemory");
    }
    ConceptDictionary conceptDictionary = RocksDbConceptDictionary.loadModel(dbPath, inMemory);
    return new DictionaryConceptDetector(conceptDictionary);
  }

  public static void runDictionaryConceptDetector(
      @NotNull ConceptsOptions conceptsOptions
  ) throws IOException, RocksDBException, InterruptedException {
    DictionaryConceptDetector conceptDetector = createConceptDetector(conceptsOptions);
    ProcessorServer server = ProcessorServerBuilder.forProcessor(conceptDetector, conceptsOptions)
        .build();
    server.start();
    server.blockUntilShutdown();
  }

  public static void main(String[] args) {
    ConceptsOptions conceptsOptions = new ConceptsOptions();
    CmdLineParser parser = new CmdLineParser(conceptsOptions);
    try {
      parser.parseArgument(args);
      runDictionaryConceptDetector(conceptsOptions);
    } catch (CmdLineException e) {
      ProcessorServerOptions.printHelp(parser, DictionaryConceptDetector.class, e, null);
    } catch (InterruptedException | IOException | RocksDBException e) {
      e.printStackTrace();
    }
  }

  @Override
  protected void process(
      @NotNull Document document,
      @NotNull JsonObject params,
      @NotNull JsonObjectBuilder result
  ) {
    LOGGER.debug("Finding concepts in document.");

    try (DetectConcepts detectConcepts = new DetectConcepts(document)) {
      detectConcepts.run();
    }
  }

  public static class ConceptsOptions extends ProcessorServerOptions {
    @Option(
        name = "--db-path",
        metaVar = "PATH_TO",
        usage = "Optional override path to the concepts dictionary."
    )
    private @Nullable Path dbPath = null;

    @Option(
        name = "--in-memory",
        metaVar = "BOOL",
        handler = ExplicitBooleanOptionHandler.class,
        usage = "Optional override whether to load the concept dictionary into memory."
    )
    private @Nullable Boolean inMemory = null;

    public Path getDbPath() {
      return dbPath;
    }

    public Boolean getInMemory() {
      return inMemory;
    }
  }

  class DetectConcepts implements AutoCloseable {
    private final Document document;

    private final LabelIndex<GenericLabel> sentences;
    private final LabelIndex<GenericLabel> posTags;
    private final LabelIndex<GenericLabel> norms;
    private final LabelIndex<GenericLabel> acronyms;
    private final Labeler<GenericLabel> termLabeler;
    private final Labeler<GenericLabel> conceptLabeler;

    private StringBuilder editedSentenceText;
    private List<Label> editedSentenceTokens;


    public DetectConcepts(Document document) {
      this.document = document;
      sentences = document.getLabelIndex("sentences");
      posTags = document.getLabelIndex("pos_tags");
      norms = document.getLabelIndex("norm_forms");
      acronyms = document.getLabelIndex("acronyms");
      termLabeler = document.getLabeler("umls_terms");
      conceptLabeler = document.getLabeler("umls_concepts");
    }

    public void run() {
      String documentText = document.getText();
      for (GenericLabel sentence : sentences) {
        LOGGER.trace("Identifying concepts in a sentence");

        editedSentenceText = new StringBuilder(sentence.coveredText(documentText));
        editedSentenceTokens = new ArrayList<>();
        List<GenericLabel> sentenceTokens = WhitespaceTokenizer.tokenize(sentence.coveredText(document));
        createEditedText(sentence, sentenceTokens);

        for (int from = 0; from < sentenceTokens.size(); from++) {
          int to = Math.min(from + SPAN_SIZE, sentenceTokens.size());
          List<GenericLabel> window = sentenceTokens.subList(from, to);

          Label first = window.get(0);

          for (int subsetSize = 1; subsetSize <= window.size(); subsetSize++) {
            List<GenericLabel> windowSubset = window.subList(0, subsetSize);
            GenericLabel last = windowSubset.get(subsetSize - 1);
            GenericLabel entire = GenericLabel.createSpan(first.getStartIndex(), last.getEndIndex());

            if (posTags.inside(entire).stream()
                .map(posTag -> PartsOfSpeech.forTag(posTag.getStringValue("tag"))).allMatch(TRIVIAL_POS::contains)) {
              continue;
            }

            if (checkPhrase(entire, entire.coveredText(documentText).toString(), subsetSize == 1, 0)) {
              continue;
            }

            int editedBegin = editedSentenceTokens.get(from).getStartIndex();
            int editedEnd = editedSentenceTokens.get(from + subsetSize - 1).getEndIndex();
            String editedSubstring = editedSentenceText.substring(editedBegin, editedEnd);
            if (checkPhrase(entire, editedSubstring, subsetSize == 1, .1)) {
              continue;
            }

            if (windowSubset.size() <= 1) {
              return;
            }

            Label phraseAsSpan = GenericLabel.createSpan(windowSubset.get(0).getStartIndex(),
                windowSubset.get(windowSubset.size() - 1).getEndIndex());
            TreeSet<String> windowNorms = new TreeSet<>();
            for (GenericLabel normForm : norms.inside(phraseAsSpan)) {
              GenericLabel posTag = posTags.firstAtLocation(normForm);

              if (posTag != null && TRIVIAL_POS.contains(PartsOfSpeech.forTag(posTag.getStringValue("tag")))) {
                continue;
              }

              windowNorms.add(normForm.getStringValue("norm"));
            }
            StringBuilder queryStringBuilder = new StringBuilder();
            for (String windowNorm : windowNorms) {
              queryStringBuilder.append(windowNorm);
            }

            List<ConceptRow> normsCUI = conceptDictionary.forNorms(queryStringBuilder.toString());
            if (normsCUI != null) {
              labelTerm(phraseAsSpan, normsCUI, .3);
            }
          }
        }
      }
    }

    private void createEditedText(GenericLabel sentence, List<GenericLabel> sentenceTokens) {
      int offset = 0;
      for (GenericLabel sentenceToken : sentenceTokens) {
        GenericLabel token = GenericLabel.createSpan(
            sentence.getStartIndex() + sentenceToken.getStartIndex(),
            sentence.getStartIndex() + sentenceToken.getEndIndex()
        );

        Label span;
        GenericLabel acronymForToken = acronyms.firstAtLocation(token);
        if (acronymForToken != null) {
          String expansion = acronymForToken.getStringValue("expansion");
          editedSentenceText.replace(offset + sentenceToken.getStartIndex(),
              offset + sentenceToken.getEndIndex(), expansion);
          offset += expansion.length() - sentenceToken.length();
          span = GenericLabel.createSpan(offset + sentenceToken.getStartIndex(),
              offset + sentenceToken.getStartIndex() + expansion.length());
        } else {
          span = GenericLabel.createSpan(offset + sentenceToken.getStartIndex(), offset + sentenceToken.getEndIndex());
        }

        editedSentenceTokens.add(span);
      }
    }

    private boolean checkPhrase(Label span, String phrase, boolean oneToken, double confMod) {
      List<ConceptRow> phraseSUI = conceptDictionary.forPhrase(phrase);

      if (phraseSUI != null) {
        labelTerm(span, phraseSUI, 1 - confMod);
        return true;
      }

      if (oneToken) {
        return false;
      }

      phraseSUI = conceptDictionary.forLowercasePhrase(phrase.toLowerCase(Locale.ENGLISH));

      if (phraseSUI != null) {
        labelTerm(span, phraseSUI, 0.6 - confMod);
        return true;
      }

      return false;
    }

    private void labelTerm(
        Label span,
        List<ConceptRow> cuis,
        double score
    ) {
      for (ConceptRow row : cuis) {
        String source = conceptDictionary.source(row.getSource());
        if (source == null) {
          source = "unknown";
          LOGGER.warn("Unknown source");
        }
        conceptLabeler.add(
            GenericLabel.withSpan(span)
                .setProperty("sui", row.getSui().toString())
                .setProperty("cui", row.getCui().toString())
                .setProperty("tui", row.getTui().toString())
                .setProperty("source", source)
                .setProperty("score", score)
        );
      }
      termLabeler.add(GenericLabel.withSpan(span));
    }

    @Override
    public void close() {
      termLabeler.close();
      conceptLabeler.close();
    }
  }
}
