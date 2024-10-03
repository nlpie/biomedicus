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

package edu.umn.biomedicus.normalization;

import edu.umn.biomedicus.common.config.Config;
import edu.umn.biomedicus.common.data.DataFiles;
import edu.umn.biomedicus.common.pos.PartOfSpeech;
import edu.umn.biomedicus.common.pos.PartsOfSpeech;
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
import org.kohsuke.args4j.Option;
import org.kohsuke.args4j.spi.ExplicitBooleanOptionHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Performs word normalization on the parse tokens in a document.
 *
 * @since 1.7.0
 */
@Processor(value = "biomedicus-normalizer",
    humanName = "SPECIALIST Normalizer",
    description = "Labels norm forms for words.",
    inputs = {
        @LabelIndexDescription(name = "pos_tags", reference = "biomedicus-tnt-tagger/pos_tags")
    },
    outputs = {
        @LabelIndexDescription(name = "norm_forms",
            description = "The labeled normalized form of a word per token.",
            properties = {
                @PropertyDescription(name = "norm", dataType = "str",
                    description = "The normal form of the word.")
            })
    })
final public class NormalizationProcessor extends DocumentProcessor {

  private static final Logger LOGGER = LoggerFactory.getLogger(NormalizationProcessor.class);

  private final NormalizerModel normalizerStore;

  /**
   * Creates a new normalizer for normalizing a document.
   *
   * @param normalizerStore the normalizer store to use.
   */
  public NormalizationProcessor(NormalizerModel normalizerStore) {
    this.normalizerStore = normalizerStore;
  }

  public static NormalizerModel loadModel(Options options) {
    DataFiles.checkDataPath();
    Path dbPath = options.getDbPath();
    boolean inMemory = options.getInMemory();
    LOGGER.info("Loading normalization dictionary from \"{}\". inMemory = {}", dbPath, inMemory);
    return RocksDBNormalizerModel.loadModel(dbPath).inMemory(inMemory);
  }

  public static NormalizationProcessor createNormalizationProcessor(Options options) {
    return new NormalizationProcessor(loadModel(options));
  }

  public static void runNormalizationProcessor(
      Options options
  ) throws IOException, InterruptedException {
    NormalizationProcessor normalizationProcessor = createNormalizationProcessor(options);
    ProcessorServer server = options.build(normalizationProcessor);
    server.start();
    server.blockUntilShutdown();
  }

  public static void main(String[] args) {
    DataFiles.checkDataPath();
    Options options = new Options();
    CmdLineParser parser = new CmdLineParser(options);
    try {
      parser.parseArgument(args);
      runNormalizationProcessor(options);
    } catch (CmdLineException e) {
      ProcessorServer.Builder.printHelp(parser, NormalizationProcessor.class, e, null);
    } catch (InterruptedException | IOException e) {
      e.printStackTrace();
    }
  }

  @Override
  protected void process(
      @NotNull Document document,
      @NotNull JsonObject params,
      @NotNull JsonObjectBuilder<?, ?> result
  ) {
    LOGGER.debug("Normalizing tokens in a document.");
    LabelIndex<GenericLabel> posTagIndex = document.getLabelIndex("pos_tags");
    try (Labeler<GenericLabel> normFormLabeler = document.getLabeler("norm_forms")) {
      for (GenericLabel posTag : posTagIndex) {
        String word = posTag.getText();
        PartOfSpeech partOfSpeech = PartsOfSpeech.forTag(posTag.getStringValue("tag"));
        String norm = normalizerStore.get(new TermPos(word, partOfSpeech));
        if (norm == null) {
          norm = word.toLowerCase();
        }
        normFormLabeler.add(GenericLabel.withSpan(posTag.getStartIndex(), posTag.getEndIndex())
            .setProperty("norm", norm));
      }
    }
  }

  public static class Options extends ProcessorServer.Builder {
    @Option(
        name = "--db-path",
        metaVar = "DB_PATH",
        usage = "Override path to the normalization dictionary."
    )
    private Path dbPath;

    @Option(
        name = "--in-memory",
        metaVar = "IN_MEMORY",
        handler = ExplicitBooleanOptionHandler.class,
        usage = "Override boolean for whether the normalization dictionary should be loaded " +
            "into memory."
    )
    private boolean inMemory;

    public Options() {
      Config config = Config.loadFromDefaultLocations();
      dbPath = Paths.get(config.getStringValue("normalization.db"));
      inMemory = config.getBooleanValue("normalization.inMemory");
    }

    public Path getDbPath() {
      return dbPath;
    }

    public void setDbPath(Path dbPath) {
      this.dbPath = dbPath;
    }

    public boolean getInMemory() {
      return inMemory;
    }

    public void setInMemory(Boolean inMemory) {
      this.inMemory = inMemory;
    }
  }
}
