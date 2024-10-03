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

package edu.umn.biomedicus.acronym;

import edu.umn.biomedicus.common.config.Config;
import edu.umn.biomedicus.common.data.DataFiles;
import edu.umn.biomedicus.common.pos.PartOfSpeech;
import edu.umn.biomedicus.common.pos.PartsOfSpeech;
import edu.umn.biomedicus.common.tokenization.WhitespaceTokenizer;
import edu.umn.biomedicus.common.tuples.Pair;
import edu.umn.biomedicus.serialization.YamlSerialization;
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
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.yaml.snakeyaml.Yaml;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * An implementation of an acronym model that uses word vectors and a cosine distance metric.
 */
@Processor(value = "biomedicus-acronyms",
    humanName = "Acronym Detector",
    description = "Labels acronyms.",
    parameters = {
        @ParameterDescription(name = "labelOtherSenses",
            description = "Whether the non-highest scoring acronym disambiguations should be labeled",
            dataType = "bool")
    },
    inputs = {
        @LabelIndexDescription(name = "pos_tags", reference = "biomedicus-tnt-tagger/pos_tags")
    },
    outputs = {
        @LabelIndexDescription(name = "acronyms",
            description = "The highest scoring acronym disambiguation for an acronym.",
            properties = {
                @PropertyDescription(name = "score", dataType = "float",
                    description = "The acronym's score."),
                @PropertyDescription(name = "expansion", dataType = "str",
                    description = "The acronym's expansion.")
            }
        ),
        @LabelIndexDescription(name = "other_acronym_senses",
            description = "The non-highest-scoring disambiguations.",
            properties = {
                @PropertyDescription(name = "score", dataType = "float",
                    description = "The acronym's score."),
                @PropertyDescription(name = "expansion", dataType = "str",
                    description = "The acronym's expansion.")
            }
        )
    }
)
public class AcronymDetectorProcessor extends DocumentProcessor {
  private static final Logger LOGGER = LoggerFactory.getLogger(AcronymDetectorProcessor.class);

  /*
   * All part of speech tags to exclude from consideration as acronyms.
   * Some of the verbs may have to change, but PRP and CC are key (esp. for tokens like "it", "or")
   */
  private static final Set<PartOfSpeech> EXCLUDE_POS = EnumSet.of(
      PartOfSpeech.PRP,
      PartOfSpeech.DT,
      PartOfSpeech.CC,
      PartOfSpeech.IN,
      PartOfSpeech.UH,
      PartOfSpeech.TO,
      PartOfSpeech.RP,
      PartOfSpeech.PDT,
      PartOfSpeech.WP,
      PartOfSpeech.WP$,
      PartOfSpeech.WDT,
      PartOfSpeech.POS,
      PartOfSpeech.MD
  );

  private final WordVectorSpace wordVectorSpace;

  private final SenseVectors senseVectors;

  private final Map<String, Collection<String>> expansions;

  @Nullable
  private final OrthographicAcronymModel orthographicModel;

  @Nullable
  private final AlignmentModel alignmentModel;

  private final boolean labelOtherSenses;

  private final double cutoffScore;

  AcronymDetectorProcessor(
      WordVectorSpace wordVectorSpace,
      SenseVectors senseVectors,
      Map<String, Collection<String>> expansions,
      @Nullable OrthographicAcronymModel orthographicModel,
      @Nullable AlignmentModel alignmentModel,
      boolean labelOtherSenses,
      double cutoffScore
  ) {
    this.wordVectorSpace = wordVectorSpace;
    this.senseVectors = senseVectors;
    this.expansions = expansions;
    this.orthographicModel = orthographicModel;
    this.alignmentModel = alignmentModel;
    this.labelOtherSenses = labelOtherSenses;
    this.cutoffScore = cutoffScore;
  }

  /**
   * Will return a list of the possible senses for this acronym
   *
   * @param token a Token
   * @return a List of Strings of all possible senses
   */
  public Collection<String> getExpansions(CharSequence token) {
    String acronym = Acronyms.standardAcronymForm(token);
    Collection<String> result = expansions.get(acronym);
    if (result != null) {
      return result;
    }
    return Collections.emptyList();
  }

  /**
   * Does the model know about this acronym?
   *
   * @param token a token
   * @return true if this token's text is a known acronym
   */
  public boolean hasAcronym(CharSequence token) {
    String acronym = Acronyms.standardAcronymForm(token);
    return expansions.containsKey(acronym);
  }

  /**
   * Will return the model's best guess for the sense of this acronym
   *
   * @param context a list of tokens including the full context for this acronym
   * @param index   an integer specifying the index of the acronym
   */
  public List<ScoredSense> findBestSense(List<CharSequence> context, int index) {
    String acronym = Acronyms.standardAcronymForm(context.get(index));
    // If the model doesn't contain this acronym, make sure it doesn't contain an upper-case version
    Collection<String> senses = expansions.get(acronym);
    if (senses == null) {
      senses = expansions.get(acronym.toUpperCase());
    }
    if (senses == null) {
      // Delete non-word characters.
      senses = expansions.get(acronym.replaceAll("[\\W]", ""));
    }
    if (senses == null) {
      senses = expansions.get(acronym.toLowerCase());
    }
    if (senses == null && alignmentModel != null) {
      senses = alignmentModel.findBestLongforms(acronym);
    }
    if (senses == null || senses.size() == 0) {
      return Collections.emptyList();
    }

    // If the acronym is unambiguous, our work is done
    if (senses.size() == 1) {
      return Collections.singletonList(new ScoredSense(senses.iterator().next(), 1));
    }

    List<Pair<String, SparseVector>> usableSenses = new ArrayList<>();
    // Be sure that there even are disambiguation vectors for senses
    for (String sense : senses) {
      SparseVector sparseVector = senseVectors.get(sense);
      if (sparseVector != null) {
        usableSenses.add(Pair.of(sense, sparseVector));
      }
    }

    // If no senses good for disambiguation were found, try the upper-case version
    if (usableSenses.size() == 0 && expansions.containsKey(acronym.toUpperCase())) {
      for (String sense : senses) {
        SparseVector sparseVector = senseVectors.get(sense);
        if (sparseVector != null) {
          usableSenses.add(Pair.of(sense, sparseVector));
        }
      }
    }

    // Should this just guess the first sense instead?
    if (usableSenses.size() == 0) {
      return Collections.emptyList();
    }

    SparseVector vector = wordVectorSpace.vectorize(context, index);
    // Loop through all possible senses for this acronym
    return usableSenses.stream()
        .map(pair -> {
          double score = vector.dot(pair.getSecond());
          return new ScoredSense(pair.first(), score);
        })
        .filter(scored -> scored.getScore() >= cutoffScore)
        .sorted(Comparator.comparing(ScoredSense::getScore).reversed())
        .collect(Collectors.toList());
  }

  /**
   * Remove a single word from the model
   *
   * @param word the word to remove
   */
  public void removeWord(String word) {
    Integer ind = wordVectorSpace.removeWord(word);
    if (ind != null) {
      senseVectors.removeWord(ind);
    }
  }

  /**
   * Remove all words from the model except those given
   *
   * @param wordsToRemove the set of words to keep
   */
  public void removeWordsExcept(Set<String> wordsToRemove) {
    Set<Integer> removed = wordVectorSpace.removeWordsExcept(wordsToRemove);
    removed.remove(null);
    senseVectors.removeWords(removed);
  }

  void writeToDirectory(Path outputDir,
                        @Nullable Map<String, SparseVector> senseVectors) throws IOException {
    Yaml yaml = YamlSerialization.createYaml();

    if (alignmentModel != null) {
      yaml.dump(alignmentModel, Files.newBufferedWriter(outputDir.resolve("alignment.yml")));
    }
    yaml.dump(wordVectorSpace, Files.newBufferedWriter(outputDir.resolve("vectorSpace.yml")));

    if (senseVectors != null) {
      RocksDBSenseVectors rocksDBSenseVectors = new RocksDBSenseVectors(
          outputDir.resolve("senseVectors"), true);
      rocksDBSenseVectors.putAll(senseVectors);
      rocksDBSenseVectors.close();
    }
  }

  @Override
  protected void process(
      @NotNull Document document,
      @NotNull JsonObject params,
      @NotNull JsonObjectBuilder<?, ?> result
  ) {
    LOGGER.debug("Detecting acronyms in a document.");
    Boolean labelOtherSenses = params.getBooleanValue("label_other_senses");
    if (labelOtherSenses == null) {
      labelOtherSenses = this.labelOtherSenses;
    }

    LabelIndex<GenericLabel> posTags = document.getLabelIndex("pos_tags");
    List<GenericLabel> tokens = WhitespaceTokenizer.tokenize(document);
    List<CharSequence> tokensText = tokens.stream().map(Label::getText)
        .collect(Collectors.toList());
    try (
        Labeler<GenericLabel> acronymLabeler = document.getLabeler("acronyms");
        Labeler<GenericLabel> otherSenseLabeler = document.getLabeler("all_acronym_senses")
    ) {
      int size = tokens.size();
      for (int i = 0; i < size; i++) {
        GenericLabel token = tokens.get(i);
        List<GenericLabel> partOfSpeechLabelsForToken = posTags.inside(token).asList();
        if (!allExcluded(partOfSpeechLabelsForToken)) {
          CharSequence tokenText = token.getText();
          if (hasAcronym(tokenText) || (orthographicModel != null && orthographicModel.seemsLikeAbbreviation(tokenText))) {
            List<ScoredSense> senses = findBestSense(tokensText, i);
            if (senses.size() > 0) {
              ScoredSense first = senses.get(0);
              acronymLabeler.add(GenericLabel.withSpan(token)
                  .setProperty("score", first.getScore())
                  .setProperty("expansion", first.getSense()));
              if (labelOtherSenses) {
                for (ScoredSense sense : senses) {
                  otherSenseLabeler.add(GenericLabel.withSpan(token)
                      .setProperty("score", sense.getScore())
                      .setProperty("expansion", sense.getSense()));
                }
              }
            }
          }
        }
      }
    }
  }

  @Override
  public void shutdown() {
      try {
        senseVectors.close();
      } catch (IOException e) {
        LOGGER.error("Error closing sense vectors dictionary", e);
      }
  }

  private boolean allExcluded(List<GenericLabel> posTags) {
    return posTags.stream()
        .map(tagLabel -> PartsOfSpeech.forTag(tagLabel.getStringValue("tag")))
        .allMatch(EXCLUDE_POS::contains);
  }

  public static class Settings extends ProcessorServer.Builder {
    @Option(
        name = "--acronym-vector-space",
        metaVar = "PATH",
        usage = "Path to the vector space model."
    )
    private Path vectorSpace;

    @Option(
        name = "--acronym-sense-map",
        metaVar = "PATH",
        usage = "Path to the sense map."
    )
    private Path senseMap;

    @Option(
        name = "--acronym-sense-vectors-in-memory",
        metaVar = "BOOL",
        handler = ExplicitBooleanOptionHandler.class,
        usage = "Stores sense vectors in memory"
    )
    private Boolean sensesInMemory;

    @Option(
        name = "--acronym-orthographic-model",
        metaVar = "PATH",
        usage = "The path to the orthographic model."
    )
    private Path orthographicModel;

    @Option(
        name = "--acronym-expansion-model-path",
        metaVar = "PATH",
        usage = "Path to the acronym expansions model."
    )
    private Path expansionsModel;

    @Option(
        name = "--acronym-use-alignment",
        usage = "Flag to use the alignment model."
    )
    private boolean useAlignment;

    @Option(
        name = "--acronym-alignment-model",
        metaVar = "PATH",
        usage = "Path to the acronym alignment model."
    )
    private Path alignmentModel;

    @Option(
        name = "--acronym-label-other-senses",
        metaVar = "BOOL",
        handler = ExplicitBooleanOptionHandler.class,
        usage = "Whether to label additional senses."
    )
    private boolean labelOtherSenses;

    @Option(
        name = "--acronym-cutoff-score",
        metaVar = "FLOAT",
        usage = "The acronym cutoff score."
    )
    private double cutoffScore;

    public Settings(Config config) {
      vectorSpace = Paths.get(config.getStringValue("acronym.vector.model"));
      senseMap = Paths.get(config.getStringValue("acronym.senseMap.senseVectors"));
      sensesInMemory = config.getBooleanValue("acronym.senseMap.inMemory");
      orthographicModel = Paths.get(config.getStringValue("acronym.orthographicModel"));
      expansionsModel = Paths.get(config.getStringValue("acronym.expansionsModel"));
      useAlignment = config.getBooleanValue("acronym.useAlignment");
      alignmentModel = Paths.get(config.getStringValue("acronym.alignmentModel"));
      labelOtherSenses = config.getBooleanValue("acronym.labelOtherSenses");
      cutoffScore = config.getDoubleValue("acronym.cutoffScore");
    }

    public Path getVectorSpace() {
      return vectorSpace;
    }

    public void setVectorSpace(Path vectorSpace) {
      this.vectorSpace = vectorSpace;
    }

    public Path getSenseMap() {
      return senseMap;
    }

    public void setSenseMap(Path senseMap) {
      this.senseMap = senseMap;
    }

    public Boolean getSensesInMemory() {
      return sensesInMemory;
    }

    public void setSensesInMemory(Boolean sensesInMemory) {
      this.sensesInMemory = sensesInMemory;
    }

    public Path getOrthographicModel() {
      return orthographicModel;
    }

    public void setOrthographicModel(Path orthographicModel) {
      this.orthographicModel = orthographicModel;
    }

    public Path getExpansionsModel() {
      return expansionsModel;
    }

    public void setExpansionsModel(Path expansionsModel) {
      this.expansionsModel = expansionsModel;
    }

    public boolean isUseAlignment() {
      return useAlignment;
    }

    public void setUseAlignment(boolean useAlignment) {
      this.useAlignment = useAlignment;
    }

    public Path getAlignmentModel() {
      return alignmentModel;
    }

    public void setAlignmentModel(Path alignmentModel) {
      this.alignmentModel = alignmentModel;
    }

    public boolean isLabelOtherSenses() {
      return labelOtherSenses;
    }

    public void setLabelOtherSenses(boolean labelOtherSenses) {
      this.labelOtherSenses = labelOtherSenses;
    }

    public double getCutoffScore() {
      return cutoffScore;
    }

    public void setCutoffScore(double cutoffScore) {
      this.cutoffScore = cutoffScore;
    }

    public AcronymDetectorProcessor build() throws IOException {
      DataFiles.checkDataPath();
      LOGGER.info("Loading acronym vector space: {}", vectorSpace);
      WordVectorSpace wordVectorSpace = WordVectorSpace.load(vectorSpace);
      LOGGER.info("Loading acronym sense map: {}. inMemory = {}", senseMap, sensesInMemory);
      @SuppressWarnings("resource")  // This is closed when the processors is shutdown.
      SenseVectors senseVectors = new RocksDBSenseVectors(senseMap, false)
          .inMemory(sensesInMemory);
      AlignmentModel alignment = null;
      if (useAlignment) {
        LOGGER.info("Loading alignment model: {}", alignmentModel);
        alignment = AlignmentModel.load(alignmentModel);
      }
      LOGGER.info("Loading acronym expansions: {}", expansionsModel);
      Map<String, Collection<String>> expansions = new HashMap<>();
      Pattern splitter = Pattern.compile("\\|");
      try (BufferedReader bufferedReader = Files.newBufferedReader(expansionsModel)) {
        String acronym;
        while ((acronym = bufferedReader.readLine()) != null) {
          String[] acronymExpansions = splitter.split(bufferedReader.readLine());
          expansions.put(Acronyms.standardAcronymForm(acronym), Arrays.asList(acronymExpansions));
        }
      }
      LOGGER.info("Loading orthographic model: {}", orthographicModel);
      OrthographicAcronymModel orthographicAcronymModel = OrthographicAcronymModel.load(orthographicModel);
      return new AcronymDetectorProcessor(wordVectorSpace, senseVectors, expansions,
          orthographicAcronymModel, alignment, labelOtherSenses, cutoffScore);
    }
  }

  public static void main(String[] args) {
    DataFiles.checkDataPath();
    Config config = Config.defaultConfig();
    Settings settings = new Settings(config);
    CmdLineParser parser = new CmdLineParser(settings);
    try {
      parser.parseArgument(args);
      AcronymDetectorProcessor processor = settings.build();
      ProcessorServer server = settings.createServer(processor);
      server.start();
      server.blockUntilShutdown();
    } catch (CmdLineException e) {
      ProcessorServer.Builder.printHelp(parser, AcronymDetectorProcessor.class, e, null);
    } catch (IOException | InterruptedException e) {
      e.printStackTrace();
    }
  }
}
