package edu.umn.biomedicus.rtf;

import edu.umn.biomedicus.rtf.reader.PlainTextSink;
import edu.umn.biomedicus.rtf.reader.RtfParser;
import edu.umn.biomedicus.rtf.reader.RtfSource;
import org.junit.jupiter.api.Test;

import java.io.BufferedInputStream;
import java.io.IOException;
import java.io.InputStream;

import static org.junit.jupiter.api.Assertions.*;

class RTFTest {
  @Test
  void parseRtf() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    try (InputStream is = Thread.currentThread().getContextClassLoader().getResourceAsStream("edu/umn/biomedicus/rtf/test.rtf")) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseFile(source, sink);
    }
    String text = sink.getText();
    assertEquals("The quick brown fox jumped over the lazy dog.\n", text);
  }
}
