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

import edu.umn.biomedicus.rtf.reader.PlainTextSink;
import edu.umn.biomedicus.rtf.reader.RtfParser;
import edu.umn.biomedicus.rtf.reader.RtfSource;
import org.junit.jupiter.api.Test;

import java.io.*;
import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.*;

class RTFTest {
  @Test
  void parseRtf() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    ClassLoader classLoader = Thread.currentThread().getContextClassLoader();
    try (InputStream is = classLoader.getResourceAsStream("edu/umn/biomedicus/rtf/test.rtf")) {
      if (is == null) {
        throw new FileNotFoundException();
      }
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("The quick brown fox jumped over the lazy dog.\n", text);
  }

  @Test
  void testUnicodeSkips() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\u8901\\'b7b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a⋅b", text);
  }

  @Test
  void testHex() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\'abb}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a«b", text);
  }

  @Test
  void testSect() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\sect b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a\n\nb", text);
  }

  @Test
  void testPage() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\page b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a\n\nb", text);
  }

  @Test
  void testColumn() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\column b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a\n\nb", text);
  }

  @Test
  void testLbr() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\lbr0 b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a\nb", text);
  }

  @Test
  void testEmdash() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\emdash b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a—b", text);
  }

  @Test
  void testEndash() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\endash b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a–b", text);
  }

  @Test
  void testEmspace() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\emspace b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a b", text);
  }

  @Test
  void testEnspace() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\enspace b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a b", text);
  }

  @Test
  void testQmspace() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\qmspace b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a b", text);
  }

  @Test
  void testBullet() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\bullet b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a•b", text);
  }

  @Test
  void testLquote() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\lquote b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a‘b", text);
  }

  @Test
  void testRquote() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\rquote b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a’b", text);
  }

  @Test
  void testLdblquote() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\ldblquote b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a“b", text);
  }

  @Test
  void testRdblquote() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\rdblquote b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a”b", text);
  }

  @Test
  void testNbsp() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\~ b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a\u00a0b", text);
  }

  @Test
  void testOptionalHyphen() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\- b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a\u00adb", text);
  }

  @Test
  void testNbHyphen() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\_ b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a‑b", text);
  }

  @Test
  void testZwbo() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\zwbo b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a\u200bb", text);
  }

  @Test
  void testZwnbo() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\zwnbo b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a\ufeffb", text);
  }

  @Test
  void testZwj() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\zwj b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a\u200db", text);
  }
  
  @Test
  void testZwnj() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\zwnj b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("a\u200cb", text);
  }

  @Test
  void testHiddenFormatting() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\v bmk\\plain b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("ab", text);
  }

  @Test
  void testHiddenFormattingUnicode() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\v \\uc0\\u9786\\plain b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("ab", text);
  }

  @Test
  void testHiddenFormattingHex() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\v \\'AB\\plain b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("ab", text);
  }

  @Test
  void testHiddenOutputKeyword() throws IOException {
    RtfParser parser = RTF.getParser();
    PlainTextSink sink = new PlainTextSink();
    String tested = "{\\rtf1 a\\v \\emdash\\plain b}";
    try (InputStream is = new ByteArrayInputStream(tested.getBytes(StandardCharsets.US_ASCII))) {
      RtfSource source = new RtfSource(new BufferedInputStream(is));
      parser.parseRtf(source, sink);
    }
    String text = sink.getText();
    assertEquals("ab", text);
  }
}
