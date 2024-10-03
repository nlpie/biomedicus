/*
 * Copyright 2022 Regents of the University of Minnesota.
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

import edu.umn.biomedicus.common.exc.BiomedicusException;
import edu.umn.nlpie.mtap.common.JsonObject;
import edu.umn.nlpie.mtap.common.JsonObjectBuilder;
import edu.umn.nlpie.mtap.model.Document;
import edu.umn.nlpie.mtap.model.GenericLabel;
import edu.umn.nlpie.mtap.model.LabelIndex;
import edu.umn.nlpie.mtap.processing.DocumentProcessor;
import edu.umn.nlpie.mtap.processing.Processor;
import edu.umn.nlpie.mtap.processing.ProcessorServer;
import org.jetbrains.annotations.NotNull;
import org.kohsuke.args4j.Argument;
import org.kohsuke.args4j.CmdLineException;
import org.kohsuke.args4j.CmdLineParser;

import java.io.IOException;
import java.nio.file.Path;
import java.util.List;

/**
 * Trains the TnT model using tagged parts of speech in documents.
 *
 * @author Ben Knoll
 * @since 1.7
 */
@Processor("biomedicus-tnt-trainer")
public class TntTrainerProcessor extends DocumentProcessor {
  private final TntModelTrainer tntModelTrainer;

  private final Path outputDir;

  public TntTrainerProcessor(@NotNull Path outputDir, @NotNull DataStoreFactory dataStoreFactory) {
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
  protected void process(@NotNull Document document,
                         @NotNull JsonObject params,
                         @NotNull JsonObjectBuilder<?, ?> result) {
    LabelIndex<GenericLabel> sentences = document.getLabelIndex("sentences");
    LabelIndex<GenericLabel> partsOfSpeech = document.getLabelIndex("pos_tags");
    for (GenericLabel sentence : sentences) {
      List<GenericLabel> sentencesPos = partsOfSpeech.inside(sentence).asList();
      tntModelTrainer.addSentence(sentencesPos);
    }
  }

  @Override
  public void shutdown() {
    System.out.println("Shutting down tnt trainer, writing model to " + outputDir);
    try {
      tntModelTrainer.createModel().write(outputDir);
    } catch (IOException e) {
      throw new BiomedicusException(e);
    }
  }

  public static TntTrainerProcessor createTrainer(Path outputDir) {
    RocksDbDataStoreFactory dataStoreFactory = new RocksDbDataStoreFactory(
        outputDir.resolve("words/"), false
    );
    return new TntTrainerProcessor(outputDir, dataStoreFactory);
  }

  public static void hostProcessor(Options options) throws IOException, InterruptedException {
    Path outputDir = options.getOutputDir();
    TntTrainerProcessor trainer = createTrainer(outputDir);
    ProcessorServer server = options.build(trainer);
    server.start();
    server.blockUntilShutdown();
  }

  public static void main(String[] args) {
    Options options = new Options();
    CmdLineParser parser = new CmdLineParser(options);
    try {
      parser.parseArgument(args);
      hostProcessor(options);
    } catch (CmdLineException e) {
      ProcessorServer.Builder.printHelp(parser, TntTrainerProcessor.class, e, null);
    } catch (InterruptedException | IOException e) {
      e.printStackTrace();
    }
  }

  public static class Options extends ProcessorServer.Builder {
    @Argument(
        metaVar = "OUTPUT_PATH",
        required = true,
        usage = "The output directory where the finished model should be written."
    )
    private Path outputDir;

    public Path getOutputDir() {
      return outputDir;
    }

    public void setOutputDir(Path outputDir) {
      this.outputDir = outputDir;
    }
  }
}
