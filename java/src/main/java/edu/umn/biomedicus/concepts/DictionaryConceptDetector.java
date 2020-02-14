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
import edu.umn.biomedicus.normalization.NormalizationProcessor;
import edu.umn.biomedicus.normalization.NormalizerModel;
import edu.umn.biomedicus.normalization.TermPos;
import edu.umn.nlpie.mtap.common.JsonObject;
import edu.umn.nlpie.mtap.common.JsonObjectBuilder;
import edu.umn.nlpie.mtap.model.*;
import edu.umn.nlpie.mtap.processing.*;
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
import java.nio.file.Paths;
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
    humanName = "UMLS Concept Detector",
    description = "Labels UMLS Concepts",
    inputs = {
        @LabelIndexDescription(name = "sentences", reference = "biomedicus-sentences/sentences"),
        @LabelIndexDescription(name = "pos_tags", reference = "biomedicus-tnt-tagger/pos_tags"),
        @LabelIndexDescription(name = "norm_forms",
            reference = "biomedicus-normalizer/norm_forms",
            optional = true),
        @LabelIndexDescription(name = "acronyms", reference = "biomedicus-acronyms/acronyms")
    },
    outputs = {
        @LabelIndexDescription(name = "umls_concepts",
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
        @LabelIndexDescription(name = "umls_terms",
            description = "Text that is covered by one or more concepts.")
    }
)
class DictionaryConceptDetector extends DocumentProcessor {

  private static final Logger LOGGER = LoggerFactory.getLogger(DictionaryConceptDetector.class);

  private static final Set<PartOfSpeech> TRIVIAL_POS = buildTrivialPos();

  private static final int SPAN_SIZE = 5;

  private final ConceptDictionary conceptDictionary;

  @Nullable
  private final NormalizerModel normalizerModel;

  DictionaryConceptDetector(ConceptDictionary conceptDictionary, @Nullable NormalizerModel normalizerModel) {
    this.conceptDictionary = conceptDictionary;
    this.normalizerModel = normalizerModel;
  }

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

    ConceptDictionary conceptDictionary = loadConceptsDictionary(conceptsOptions);
    NormalizerModel normalizerModel = null;
    if (conceptsOptions.getNormalizeLocally()) {
      NormalizationProcessor.Options normalizerOptions = new NormalizationProcessor.Options();
      normalizerOptions.setDbPath(conceptsOptions.getNormalizerModel());
      normalizerOptions.setInMemory(conceptsOptions.getNormalizerModelInMemory());
      normalizerModel = NormalizationProcessor.loadModel(normalizerOptions);
    }
    return new DictionaryConceptDetector(conceptDictionary, normalizerModel);
  }

  @NotNull
  public static ConceptDictionary loadConceptsDictionary(
      @NotNull DictionaryConceptDetector.ConceptsOptions conceptsOptions
  ) throws RocksDBException, IOException {
    return RocksDbConceptDictionary.loadModel(conceptsOptions.getDbPath(), conceptsOptions.getInMemory());
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
    private @Nullable Path dbPath;

    @Option(
        name = "--in-memory",
        metaVar = "BOOL",
        handler = ExplicitBooleanOptionHandler.class,
        usage = "Optional override whether to load the concept dictionary into memory."
    )
    private boolean inMemory;

    @Option(
        name = "--normalize-locally",
        metaVar = "BOOL",
        handler = ExplicitBooleanOptionHandler.class,
        usage = "Normalize here in the concept detector instead of using a norms index."
    )
    private boolean normalizeLocally;

    @Option(
        name = "--normalizer-model",
        metaVar = "PATH_TO_NORMALIZER_MODEL",
        usage = "Optional override for the normalizer model path"
    )
    private @Nullable Path normalizerModel;

    @Option(
        name = "--normalizer-model-in-memory",
        metaVar = "BOOL",
        handler = ExplicitBooleanOptionHandler.class,
        usage = "Optional override for whether to load the normalization model into memory."
    )
    private boolean normalizerModelInMemory;

    public ConceptsOptions() {
      DataFiles.checkDataPath();
      Config config = Config.loadFromDefaultLocations();
      dbPath = Paths.get(config.getStringValue("concepts.db"));
      inMemory = config.getBooleanValue("concepts.inMemory");
      normalizeLocally = config.getBooleanValue("concepts.normalizeLocally");
      normalizerModel = Paths.get(config.getStringValue("normalization.db"));
      normalizerModelInMemory = config.getBooleanValue("normalization.inMemory");
    }

    public @Nullable Path getDbPath() {
      return dbPath;
    }

    public boolean getInMemory() {
      return inMemory;
    }

    public boolean getNormalizeLocally() {
      return normalizeLocally;
    }

    public @Nullable Path getNormalizerModel() {
      return normalizerModel;
    }

    public boolean getNormalizerModelInMemory() {
      return normalizerModelInMemory;
    }

    public void setDbPath(@Nullable Path dbPath) {
      this.dbPath = dbPath;
    }

    public void setInMemory(boolean inMemory) {
      this.inMemory = inMemory;
    }

    public void setNormalizeLocally(boolean normalizeLocally) {
      this.normalizeLocally = normalizeLocally;
    }

    public void setNormalizerModel(@Nullable Path normalizerModel) {
      this.normalizerModel = normalizerModel;
    }

    public void setNormalizerModelInMemory(boolean normalizerModelInMemory) {
      this.normalizerModelInMemory = normalizerModelInMemory;
    }
  }

  class DetectConcepts implements AutoCloseable {
    private final Document document;

    private final LabelIndex<GenericLabel> sentences;
    private final LabelIndex<GenericLabel> posTags;
    private final LabelIndex<GenericLabel> acronyms;
    private final Labeler<GenericLabel> termLabeler;
    private final Labeler<GenericLabel> conceptLabeler;

    private StringBuilder editedSentenceText;
    private List<Label> editedSentenceTokens;
    private List<Boolean> edited;


    public DetectConcepts(Document document) {
      this.document = document;
      sentences = document.getLabelIndex("sentences");
      posTags = document.getLabelIndex("pos_tags");
      acronyms = document.getLabelIndex("acronyms");
      termLabeler = document.getLabeler("umls_terms");
      conceptLabeler = document.getLabeler("umls_concepts");
    }

    public void run() {
      LabelIndex<GenericLabel> norms = null;
      if (normalizerModel == null) {
        norms = document.getLabelIndex("norm_forms");
      }
      for (GenericLabel sentence : sentences) {
        LOGGER.trace("Identifying concepts in a sentence");

        editedSentenceText = new StringBuilder(sentence.getText());
        editedSentenceTokens = new ArrayList<>();
        edited = new ArrayList<>();
        List<GenericLabel> sentenceTokens = posTags.inside(sentence).asList();
        createEditedText(sentence, sentenceTokens);

        List<String> sentenceNorms = new ArrayList<>();
        if (normalizerModel != null) {
          for (GenericLabel sentenceToken : sentenceTokens) {
            String word = sentenceToken.getText();
            PartOfSpeech tag = PartsOfSpeech.forTag(sentenceToken.getStringValue("tag"));
            String norm = normalizerModel.get(new TermPos(word, tag));
            if (norm == null) norm = word.toLowerCase();
            sentenceNorms.add(norm);
          }
        } else {
          for (GenericLabel genericLabel : norms.inside(sentence)) {
            sentenceNorms.add(genericLabel.getStringValue("norm"));
          }
        }


        for (int from = 0; from < sentenceTokens.size(); from++) {
          int to = Math.min(from + SPAN_SIZE, sentenceTokens.size());
          List<GenericLabel> window = sentenceTokens.subList(from, to);

          Label first = window.get(0);

          for (int subsetSize = 1; subsetSize <= window.size(); subsetSize++) {
            List<GenericLabel> windowSubset = window.subList(0, subsetSize);
            GenericLabel last = windowSubset.get(subsetSize - 1);
            GenericLabel entire = GenericLabel.withSpan(first.getStartIndex(), last.getEndIndex())
                .withDocument(document).build();

            if (window.stream()
                .map(posTag -> PartsOfSpeech.forTag(posTag.getStringValue("tag"))).allMatch(TRIVIAL_POS::contains)) {
              continue;
            }

            String phrase = entire.getText();
            if (checkPhrase(entire, phrase, subsetSize == 1, 0)) {
              continue;
            }

            if (edited.subList(from, from + subsetSize).stream().anyMatch(i -> i)) {
              int editedBegin = editedSentenceTokens.get(from).getStartIndex();
              int editedEnd = editedSentenceTokens.get(from + subsetSize - 1).getEndIndex();
              String editedSubstring = editedSentenceText.substring(editedBegin, editedEnd);
              if (checkPhrase(entire, editedSubstring, subsetSize == 1, .1)) {
                  continue;
                }
            }

            if (windowSubset.size() <= 1) {
              continue;
            }

            List<String> windowNorms = new ArrayList<>(sentenceNorms.subList(from, to));
            windowNorms.sort(Comparator.naturalOrder());
            StringBuilder queryStringBuilder = new StringBuilder();
            for (String windowNorm : windowNorms) {
              queryStringBuilder.append(windowNorm);
            }
            List<ConceptRow> normsCUI = conceptDictionary.forNorms(queryStringBuilder.toString());
            if (normsCUI != null) {
              labelTerm(entire, normsCUI, .3);
            }
          }
        }
      }
    }

    private void createEditedText(GenericLabel sentence, List<GenericLabel> sentenceTokens) {
      int offset = 0;
      for (GenericLabel sentenceToken : sentenceTokens) {
        Label span;
        GenericLabel acronymForToken = acronyms.firstAtLocation(sentenceToken);
        if (acronymForToken != null) {
          edited.add(true);
          String expansion = acronymForToken.getStringValue("expansion");
          editedSentenceText.replace(offset + sentenceToken.getStartIndex() - sentence.getStartIndex(),
              offset + sentenceToken.getEndIndex() - sentence.getStartIndex(), expansion);
          span = GenericLabel.createSpan(offset + sentenceToken.getStartIndex() - sentence.getStartIndex(),
              offset + sentenceToken.getStartIndex() + expansion.length() - sentence.getStartIndex());
          offset += expansion.length() - sentenceToken.length();
        } else {
          edited.add(false);
          span = GenericLabel.createSpan(offset + sentenceToken.getStartIndex() - sentence.getStartIndex(), offset + sentenceToken.getEndIndex() - sentence.getStartIndex());
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
