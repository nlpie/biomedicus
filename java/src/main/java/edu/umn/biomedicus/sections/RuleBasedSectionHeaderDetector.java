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

package edu.umn.biomedicus.sections;

import edu.umn.biomedicus.common.config.Config;
import edu.umn.biomedicus.common.data.DataFiles;
import edu.umn.biomedicus.common.utilities.Patterns;
import edu.umn.nlpie.mtap.common.JsonObject;
import edu.umn.nlpie.mtap.common.JsonObjectBuilder;
import edu.umn.nlpie.mtap.model.*;
import edu.umn.nlpie.mtap.processing.*;
import org.jetbrains.annotations.NotNull;
import org.kohsuke.args4j.CmdLineException;
import org.kohsuke.args4j.CmdLineParser;
import org.kohsuke.args4j.Option;

import java.io.IOException;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * Section detector based off rules for clinical notes.
 *
 * @author Ben Knoll
 * @author Yan Wang (rules)
 * @since 1.4
 */
@Processor(value = "biomedicus-section-headers",
    humanName = "Section Header Detector",
    description = "Detects section headers using a regex pattern.",
    inputs = {
        @LabelIndexDescription(name = "sentences", reference = "biomedicus-sentences/sentences"),
        @LabelIndexDescription(name = "bold", reference = "biomedicus-rtf-processor/bold", optional = true),
        @LabelIndexDescription(name = "underlined", reference = "biomedicus-rtf-processor/underlined", optional = true)
    },
    outputs = {
        @LabelIndexDescription(name = "section_headers", description = "Section Headers")
    })
public class RuleBasedSectionHeaderDetector extends DocumentProcessor {

  private final Pattern headers;

  /**
   * Injectable constructor.
   *
   * @param headers patterns for the headers.
   */
  RuleBasedSectionHeaderDetector(Pattern headers) {
    this.headers = headers;
  }

  @Override
  protected void process(@NotNull Document document, @NotNull JsonObject params, @NotNull JsonObjectBuilder<?, ?> result) {
    LabelIndex<GenericLabel> sentenceLabelIndex = document.getLabelIndex("sentences");
    Map<String, LabelIndex<?>> labelIndices = document.getLabelIndices();

    LabelIndex<GenericLabel> boldLabelIndex = null;
    if (labelIndices.containsKey("bold")) {
      boldLabelIndex = document.getLabelIndex("bold");
    }
    LabelIndex<GenericLabel> underlinedLabelIndex = null;
    if (labelIndices.containsKey("underlined")) {
      underlinedLabelIndex = document.getLabelIndex("underlined");
    }

    try (Labeler<Label> labeler = document.getLabeler("section_headers")) {
      for (GenericLabel sentenceLabel : sentenceLabelIndex) {
        CharSequence sentenceText = sentenceLabel.getText();
        if (headers.matcher(sentenceText).find() ||
            (boldLabelIndex != null && !boldLabelIndex.atLocation(sentenceLabel).isEmpty()) ||
            (underlinedLabelIndex != null && !underlinedLabelIndex.atLocation(sentenceLabel).isEmpty())) {
          labeler.add(GenericLabel.withSpan(sentenceLabel).build());
        }
      }
    }
  }

  public static class Options extends ProcessorServer.Builder {
    @Option(
        name = "--pattern-path",
        metaVar = "PATH",
        usage = "Override for the file containing section header patterns."
    )
    private Path pattern;

    public Options() {
      Config config = Config.loadFromDefaultLocations();
      pattern = Paths.get(config.getStringValue("sections.headersFile"));
    }

    public Path getPattern() {
      return pattern;
    }
  }

  public static RuleBasedSectionHeaderDetector createSectionHeaderDetector(
      Options options
  ) throws IOException {
    return new RuleBasedSectionHeaderDetector(
        Patterns.loadPatternByJoiningLines(options.getPattern())
    );
  }

  public static void runSectionHeaderDetector(
      Options options
  ) throws IOException, InterruptedException {
    RuleBasedSectionHeaderDetector sectionHeaderDetector = createSectionHeaderDetector(options);
    ProcessorServer server = options.createServer(sectionHeaderDetector);
    server.start();
    server.blockUntilShutdown();
  }

  public static void main(String[] args) {
    DataFiles.checkDataPath();
    Options options = new Options();
    CmdLineParser parser = new CmdLineParser(options);
    try {
      parser.parseArgument(args);
      runSectionHeaderDetector(options);
    } catch (CmdLineException e) {
      ProcessorServer.Builder.printHelp(parser, RuleBasedSectionHeaderDetector.class, e, null);
    } catch (InterruptedException | IOException e) {
      e.printStackTrace();
    }
  }
}
