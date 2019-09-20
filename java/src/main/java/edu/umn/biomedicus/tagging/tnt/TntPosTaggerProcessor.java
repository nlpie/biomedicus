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

package edu.umn.biomedicus.tagging.tnt;

import edu.umn.biomedicus.common.config.Config;
import edu.umn.biomedicus.common.data.DataFiles;
import edu.umn.biomedicus.common.grams.Ngram;
import edu.umn.biomedicus.common.pos.PartOfSpeech;
import edu.umn.biomedicus.common.tuples.PosCap;
import edu.umn.biomedicus.common.tuples.WordCap;
import edu.umn.biomedicus.common.viterbi.Viterbi;
import edu.umn.biomedicus.common.viterbi.ViterbiProcessor;
import edu.umn.biomedicus.tokenization.TokenResult;
import edu.umn.biomedicus.tokenization.Tokenizer;
import edu.umn.nlpnewt.common.JsonObject;
import edu.umn.nlpnewt.common.JsonObjectBuilder;
import edu.umn.nlpnewt.model.Document;
import edu.umn.nlpnewt.model.GenericLabel;
import edu.umn.nlpnewt.model.LabelIndex;
import edu.umn.nlpnewt.model.Labeler;
import edu.umn.nlpnewt.processing.*;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.kohsuke.args4j.CmdLineException;
import org.kohsuke.args4j.CmdLineParser;
import org.kohsuke.args4j.Option;
import org.kohsuke.args4j.spi.ExplicitBooleanOptionHandler;

import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Iterator;
import java.util.List;

/**
 * Part of speech tagger implementation for the TnT algorithm.
 *
 * @author Ben Knoll
 * @since 1.0.0
 */
@Processor(value = "biomedicus-tnt-tagger",
    description = "Labels part of speech tags on the document.",
    parameters = {
        @ParameterDescription(name = "sentences_index", dataType = "str",
            description = "The name of the index containing sentences. Defaults to \"sentences\""),
        @ParameterDescription(name = "target_index", dataType = "str",
            description = "The target index to create for POS tags. Defaults to \"pos_tags\""),
        @ParameterDescription(name = "token_index", dataType = "str",
            description = "The name of an index creating tokens. By default the processor will " +
                "do tokenization on its own.")
    },
    inputs = {
        @LabelIndexDescription(name = "sentences", nameFromParameter = "sentences_index"),
        @LabelIndexDescription(nameFromParameter = "token_index", optional = true,
            description = "Existing tokens to use. Otherwise will tokenize each sentence.")
    },
    outputs = {
        @LabelIndexDescription(name = "pos_tags", nameFromParameter = "target_index",
            description = "Labeled part of speech tags on tokens.",
            properties = {
                @PropertyDescription(name = "tag", dataType = "str",
                    description = "The penn-treebank tag for the token.")
            })
    }
)
public class TntPosTaggerProcessor extends DocumentProcessor {

  /**
   * A pos cap for before the beginning of sentences.
   */
  public static final PosCap BBS = PosCap.getNotCapitalized(PartOfSpeech.BBS);

  /**
   * The pos cap for the beginning of the sentence.
   */
  public static final PosCap BOS = PosCap.getNotCapitalized(PartOfSpeech.BOS);

  /**
   * The pos cap for skipping
   */
  public static final PosCap SKIP = PosCap.getNotCapitalized(PartOfSpeech.XX);

  /**
   * The pos cap for end of sentences.
   */
  public static final PosCap EOS = PosCap.getNotCapitalized(PartOfSpeech.EOS);

  /**
   * The beam threshold in log base 10. Difference from most probable to exclude.
   */
  private final double beamThreshold;

  /**
   * The tnt model to use.
   */
  private final TntModel tntModel;

  /**
   * Default constructor. Initializes the beam threshold and tnt model.
   *
   * @param tntModel      tnt model.
   * @param beamThreshold beam threshold in log base 10. The difference from the most probable to
   *                      exclude.
   */
  public TntPosTaggerProcessor(@NotNull TntModel tntModel, double beamThreshold) {
    this.tntModel = tntModel;
    this.beamThreshold = beamThreshold;
  }

  public static TntPosTaggerProcessor createTaggerProcessor(
      TntOptions tntOptions
  ) throws IOException {
    Config config = Config.loadFromDefaultLocations();
    DataFiles dataFiles = new DataFiles();
    Path wordDB = tntOptions.getWordDB();
    if (wordDB == null) {
      wordDB = dataFiles.getDataFile(config.getStringValue("tnt.word.db"));
    }
    Path wordMetadata = tntOptions.getWordMetadata();
    if (wordMetadata == null) {
      wordMetadata = dataFiles.getDataFile(config.getStringValue("tnt.word.metadata"));
    }
    Boolean inMemory = tntOptions.getInMemory();
    if (inMemory == null) {
      inMemory = config.getBooleanValue("tnt.word.inMemory");
    }
    Path trigram = tntOptions.getTrigram();
    if (trigram == null) {
      trigram = dataFiles.getDataFile(config.getStringValue("tnt.trigram"));
    }
    Double beamThreshold = tntOptions.getBeamThreshold();
    if (beamThreshold == null) {
      beamThreshold = config.getDoubleValue("tnt.beam.threshold");
    }
    RocksDbDataStoreFactory dataStoreFactory = new RocksDbDataStoreFactory(wordDB, inMemory);
    TntModel tntModel = TntModel.load(trigram, wordMetadata, dataStoreFactory);
    return new TntPosTaggerProcessor(tntModel, beamThreshold);
  }

  public static void runTntProcessor(
      TntOptions tntOptions
  ) throws IOException, InterruptedException {
    TntPosTaggerProcessor taggerProcessor = createTaggerProcessor(tntOptions);
    ProcessorServer server = ProcessorServerBuilder.forProcessor(taggerProcessor, tntOptions)
        .build();
    server.start();
    server.blockUntilShutdown();
  }

  public static void main(String[] args) {
    TntOptions tntOptions = new TntOptions();
    CmdLineParser parser = new CmdLineParser(tntOptions);
    try {
      parser.parseArgument(args);
      runTntProcessor(tntOptions);
    } catch (CmdLineException e) {
      ProcessorServerOptions.printHelp(parser, TntPosTaggerProcessor.class, e, null);
    } catch (InterruptedException | IOException e) {
      e.printStackTrace();
    }
  }

  @Override
  protected void process(@NotNull Document document,
                         @NotNull JsonObject params,
                         @NotNull JsonObjectBuilder result) {
    String sentencesIndex = (String) params.getOrDefault("sentences_index", "sentences");
    LabelIndex<GenericLabel> sentenceLabelIndex = document.getLabelIndex(sentencesIndex);
    String targetIndex = (String) params.getOrDefault("target_index", "pos_tags");
    String tokenIndexName = (String) params.get("token_index");
    LabelIndex<GenericLabel> tokenIndex = null;
    if (tokenIndexName != null) {
      tokenIndex = document.getLabelIndex(tokenIndexName);
    }

    try (Labeler<GenericLabel> partOfSpeechLabeler = document.getLabeler(targetIndex)) {
      for (GenericLabel sentence : sentenceLabelIndex) {
        ViterbiProcessor<PosCap, WordCap> viterbiProcessor = Viterbi.secondOrder(tntModel, tntModel,
            Ngram.create(BBS, BOS), Ngram::create);
        List<GenericLabel> tokens;
        if (tokenIndex != null) {
          tokens = tokenIndex.inside(sentence).asList();
        } else {
          tokens = new ArrayList<>();
          CharSequence sentenceText = sentence.coveredText(document);
          for (TokenResult token : Tokenizer.tokenize(sentenceText)) {
            int startIndex = sentence.getStartIndex() + token.getStartIndex();
            int endIndex = sentence.getStartIndex() + token.getEndIndex();
            tokens.add(GenericLabel.withSpan(startIndex, endIndex).build());
          }
          if (tokens.size() > 0) {
            GenericLabel lastToken = tokens.remove(tokens.size() - 1);
            if (lastToken.getEndIndex() - lastToken.getStartIndex() > 1) {
              CharSequence tokenText = lastToken.coveredText(document);
              if (Arrays.asList('!', '?', '.').contains(tokenText.charAt(tokenText.length() - 1))) {
                tokens.add(GenericLabel.withSpan(lastToken.getStartIndex(), lastToken.getEndIndex() - 1).build());
                tokens.add(GenericLabel.withSpan(lastToken.getEndIndex() - 1, lastToken.getEndIndex()).build());
              } else {
                tokens.add(lastToken);
              }
            }
          }
        }

        for (GenericLabel token : tokens) {
          CharSequence text = token.coveredText(document);
          boolean isCapitalized = Character.isUpperCase(text.charAt(0));
          viterbiProcessor.advance(new WordCap(text.toString().toLowerCase(), isCapitalized));
          viterbiProcessor.beamFilter(beamThreshold);
        }

        List<PosCap> tags = viterbiProcessor.end(SKIP, EOS);

        if (tokens.size() + 2 != tags.size()) {
          throw new AssertionError(
              "Tags should be same size as number of tokens in sentence");
        }

        Iterator<PosCap> it = tags.subList(2, tags.size()).iterator();
        for (GenericLabel token : tokens) {
          PartOfSpeech partOfSpeech = it.next().getPartOfSpeech();
          partOfSpeechLabeler.add(GenericLabel.withSpan(token)
              .setProperty("tag", partOfSpeech.toString()));
        }
      }
    }
  }

  public static class TntOptions extends ProcessorServerOptions {
    @Option(
        name = "--trigram",
        metaVar = "PATH_TO_TRIGRAM",
        usage = "Optional override path to the trigram model."
    )
    private @Nullable Path trigram = null;

    @Option(
        name = "--word-db-path",
        metaVar = "PATH_TO_WORD_DB",
        usage = "Optional override path to the word DB model."
    )
    private @Nullable Path wordDB = null;

    @Option(
        name = "--word-metadata",
        metaVar = "PATH_TO_WORD_METADATA",
        usage = "Optional override path to the word metadata file."
    )
    private @Nullable Path wordMetadata = null;

    @Option(
        name = "--beam-threshold",
        metaVar = "BEAM_THRESHOLD_FLOAT",
        usage = "Optional override float > 0 specifying the beam search threshold to use."
    )
    private @Nullable Double beamThreshold = null;

    @Option(
        name = "--in-memory",
        metaVar = "IN_MEMORY",
        handler = ExplicitBooleanOptionHandler.class,
        usage = "Optional override true or false whether models should be loaded into memory."
    )
    private @Nullable Boolean inMemory = null;

    public Path getTrigram() {
      return trigram;
    }

    public void setTrigram(Path trigram) {
      this.trigram = trigram;
    }

    public Path getWordDB() {
      return wordDB;
    }

    public void setWordDB(Path wordDB) {
      this.wordDB = wordDB;
    }

    public Path getWordMetadata() {
      return wordMetadata;
    }

    public void setWordMetadata(Path wordMetadata) {
      this.wordMetadata = wordMetadata;
    }

    public Double getBeamThreshold() {
      return beamThreshold;
    }

    public void setBeamThreshold(Double beamThreshold) {
      this.beamThreshold = beamThreshold;
    }

    public Boolean getInMemory() {
      return inMemory;
    }

    public void setInMemory(Boolean inMemory) {
      this.inMemory = inMemory;
    }
  }
}
