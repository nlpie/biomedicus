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

package edu.umn.biomedicus.rtf.beans.keywords;

import edu.umn.biomedicus.rtf.reader.KeywordAction;
import edu.umn.biomedicus.rtf.reader.RtfSink;
import edu.umn.biomedicus.rtf.reader.RtfSource;
import edu.umn.biomedicus.rtf.reader.RtfState;

import jakarta.xml.bind.annotation.XmlRootElement;
import jakarta.xml.bind.annotation.XmlType;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.CharBuffer;
import java.util.Locale;

/**
 *
 */
@XmlRootElement
@XmlType
public class HexKeywordAction extends AbstractKeywordAction {
  private final char[] chars = new char[2];

  @Override
  public void executeAction(RtfState state, RtfSource source, RtfSink sink) throws IOException {
    for (int i = 0; i < 2; i++) {
      int code = source.read();
      chars[i] = (char) code;
    }
    int charactersToSkip = state.getCharactersToSkip();
    if (charactersToSkip > 0) {
      state.setCharactersToSkip(charactersToSkip - 1);
      return;
    }
    if (state.isSkippingDestination() || state.getPropertyValue("CharacterFormatting", "Hidden") > 0) {
      return;
    }
    byte code = (byte) Integer.parseInt(new String(chars).trim().toUpperCase(Locale.ROOT), 16);
    ByteBuffer bb = ByteBuffer.allocate(1).put(code);
    bb.rewind();
    CharBuffer decode = state.getDecoder().decode(bb);
    sink.writeCharacter(state.getDestination(), decode.get(0), getStartIndex(), source.getIndex());
  }

  @Override
  public KeywordAction copy() {
    return new HexKeywordAction();
  }
}
