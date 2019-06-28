package edu.umn.biomedicus.rtf;

import edu.umn.biomedicus.rtf.reader.RtfParser;
import edu.umn.biomedicus.rtf.reader.RtfSource;
import edu.umn.nlpnewt.*;
import org.jetbrains.annotations.NotNull;
import org.kohsuke.args4j.CmdLineException;

import java.io.BufferedInputStream;
import java.io.ByteArrayInputStream;
import java.io.IOException;

@Processor("biomedicus-rtf-processor")
public class RtfProcessor extends EventProcessor {

  private final RtfParser parser;

  public RtfProcessor() {
    parser = RTF.getParser();
  }

  public static void main(String[] args) {
    try {
      ProcessorServerOptions options = new ProcessorServerOptions(new RtfProcessor());
      options.parseArgs(args);
      Server server = Newt.createProcessorServer(options);
      server.start();
      server.blockUntilShutdown();
    } catch (CmdLineException e) {
      // pass
    } catch (IOException | InterruptedException e) {
      e.printStackTrace();
    }
  }

  @Override
  public void process(@NotNull Event event, @NotNull JsonObject params, @NotNull JsonObjectBuilder result) {
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
        NewtDocumentRtfSink rtfSink = new NewtDocumentRtfSink();
        parser.parseRtf(rtfSource, rtfSink);
        rtfSink.done(event, outputDocumentName);
      } else {
        int code;
        while ((code = bis.read()) != -1) {
          sb.append((char) code);
        }
        event.addDocument(outputDocumentName, sb.toString());
      }
    } catch (IOException e) {
      throw new IllegalStateException(e);
    }
  }
}
