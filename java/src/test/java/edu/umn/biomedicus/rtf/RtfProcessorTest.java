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

import edu.umn.nlpie.mtap.common.JsonObjectImpl;
import edu.umn.nlpie.mtap.model.Document;
import edu.umn.nlpie.mtap.model.Event;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;

import static org.junit.jupiter.api.Assertions.assertEquals;

class RtfProcessorTest {
  @Test
  void rtfDocument() throws IOException {
    ByteArrayOutputStream baos = new ByteArrayOutputStream();
    ClassLoader classLoader = Thread.currentThread().getContextClassLoader();
    try (InputStream is = classLoader.getResourceAsStream("edu/umn/biomedicus/rtf/test.rtf")) {
      if (is == null) {
        throw new FileNotFoundException();
      }
      int b;
      while ((b = is.read()) != -1) {
        baos.write(b);
      }
    }
    Event event = Event.newBuilder().eventID("1").build();
    event.getBinaryData().put("rtf", baos.toByteArray());
    RtfProcessor processor = new RtfProcessor();
    processor.process(event, JsonObjectImpl.newBuilder().build(), JsonObjectImpl.newBuilder());
    Document plaintext = event.getDocuments().get("plaintext");
    assertEquals("The quick brown fox jumped over the lazy dog.\n", plaintext.getText());
  }

  @Test
  void plaintextDocument() throws IOException {
    Event event = Event.newBuilder().eventID("1").build();
    event.getBinaryData().put("rtf", "The quick brown fox jumped over the lazy dog.\n".getBytes());
    RtfProcessor processor = new RtfProcessor();
    processor.process(event, JsonObjectImpl.newBuilder().build(), JsonObjectImpl.newBuilder());
    Document plaintext = event.getDocuments().get("plaintext");
    assertEquals("The quick brown fox jumped over the lazy dog.\n", plaintext.getText());
  }
}