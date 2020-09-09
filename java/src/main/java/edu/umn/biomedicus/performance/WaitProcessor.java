/*
 * Copyright 2020 Regents of the University of Minnesota.
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

package edu.umn.biomedicus.performance;

import edu.umn.nlpie.mtap.common.JsonObject;
import edu.umn.nlpie.mtap.common.JsonObjectBuilder;
import edu.umn.nlpie.mtap.model.Document;
import edu.umn.nlpie.mtap.processing.DocumentProcessor;
import edu.umn.nlpie.mtap.processing.Processor;
import edu.umn.nlpie.mtap.processing.ProcessorServer;
import org.jetbrains.annotations.NotNull;
import org.kohsuke.args4j.CmdLineException;
import org.kohsuke.args4j.CmdLineParser;
import org.kohsuke.args4j.Option;

import java.io.IOException;

@Processor("biomedicus-wait")
public class WaitProcessor extends DocumentProcessor {

  private final int waitTime;

  public WaitProcessor(int waitTime) {
    this.waitTime = waitTime;
  }

  @Override
  protected void process(@NotNull Document document, @NotNull JsonObject params, @NotNull JsonObjectBuilder<?, ?> result) {
    document.getText();
    try {
      Thread.sleep(waitTime);
    } catch (InterruptedException e) {
      throw new IllegalStateException(e);
    }
  }

  public static class WaitOptions extends ProcessorServer.Builder {
    @Option(name = "--wait-time", aliases = {"--w"})
    public int waitTime = 500;
  }

  public static void main(String[] args) {
    WaitOptions options = new WaitOptions();
    CmdLineParser parser = new CmdLineParser(options);
    try {
      parser.parseArgument(args);
      ProcessorServer server = options.build(new WaitProcessor(options.waitTime));
      server.start();
      server.blockUntilShutdown();
    } catch (CmdLineException e) {
      ProcessorServer.Builder.printHelp(parser, WaitProcessor.class, e, null);
    } catch (InterruptedException | IOException e) {
      e.printStackTrace();
    }
  }
}
