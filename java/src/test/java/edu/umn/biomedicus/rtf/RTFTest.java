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

import java.io.BufferedInputStream;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;

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
}
