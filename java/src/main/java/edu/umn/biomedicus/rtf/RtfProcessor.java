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

package edu.umn.biomedicus.rtf;

import edu.umn.biomedicus.common.data.DataFiles;
import edu.umn.biomedicus.rtf.reader.RtfParser;
import edu.umn.biomedicus.rtf.reader.RtfParserFactory;
import edu.umn.biomedicus.rtf.reader.RtfSource;
import edu.umn.nlpie.mtap.common.JsonObject;
import edu.umn.nlpie.mtap.common.JsonObjectBuilder;
import edu.umn.nlpie.mtap.common.Server;
import edu.umn.nlpie.mtap.model.Event;
import edu.umn.nlpie.mtap.processing.*;
import org.jetbrains.annotations.NotNull;
import org.kohsuke.args4j.CmdLineException;
import org.kohsuke.args4j.CmdLineParser;

import java.io.BufferedInputStream;
import java.io.ByteArrayInputStream;
import java.io.IOException;

@Processor(value = "biomedicus-rtf-processor",
    humanName = "RTF Reader",
    description = "Processes an RTF document into plaintext.",
    parameters = {
        @ParameterDescription(name = "binary_data_name", dataType = "str",
            description = "The name of the event binary data containing the RTF-encoded document." +
                "Defaults to \"rtf\""),
        @ParameterDescription(name = "output_document_name", dataType = "str",
            description = "The name of the document to create to hold the plaintext." +
                "Defaults to \"plaintext\"")
    },
    outputs = {
        @LabelIndexDescription(name = "bold",
            description = "Rtf bold formatting."),
        @LabelIndexDescription(name = "italic",
            description = "Rtf italic formatting."),
        @LabelIndexDescription(name = "underlined",
            description = "Rtf underlined formatting."),
    })
public class RtfProcessor extends EventProcessor {

  private final RtfParserFactory factory;

  public RtfProcessor() throws IOException {
    factory = RTF.getFactory();
  }

  public static void main(String[] args) {
    DataFiles.checkDataPath();
    ProcessorServer.Builder options = new ProcessorServer.Builder();
    CmdLineParser cmdLineParser = new CmdLineParser(options);
    try {
      cmdLineParser.parseArgument(args);
      Server server = options.build(new RtfProcessor());
      server.start();
      server.blockUntilShutdown();
    } catch (CmdLineException e) {
      // pass
    } catch (IOException | InterruptedException e) {
      e.printStackTrace();
    }
  }

  @Override
  public void process(@NotNull Event event, @NotNull JsonObject params, @NotNull JsonObjectBuilder<?, ?> result) {
    String binaryDataName = params.getStringValue("binary_data_name");
    if (binaryDataName == null) {
      binaryDataName = "rtf";
    }
    String outputDocumentName = params.getStringValue("output_document_name");
    if (outputDocumentName == null) {
      outputDocumentName = "plaintext";
    }
    try {
      byte[] bytes = event.getBinaryData().get(binaryDataName);
      ByteArrayInputStream bais = new ByteArrayInputStream(bytes);
      BufferedInputStream bis = new BufferedInputStream(bais);
      StringBuilder sb = new StringBuilder();
      bis.mark(6);
      for (int i = 0; i < 6; i++) {
        int code = bis.read();
        if (code != -1) {
          sb.append((char) code);
        }
      }
      if ("{\\rtf1".equals(sb.toString())) {
        bis.reset();
        RtfSource rtfSource = new RtfSource(bis);
        MTAPDocumentsSink sink = new MTAPDocumentsSink();
        RtfParser parser = factory.create();
        parser.parseRtf(rtfSource, sink);
        sink.done(event, outputDocumentName);
      } else {
        int code;
        while ((code = bis.read()) != -1) {
          sb.append((char) code);
        }
        event.createDocument(outputDocumentName, sb.toString());
      }
    } catch (IOException e) {
      throw new IllegalStateException(e);
    }
  }
}
