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

package edu.umn.biomedicus.rtf.reader;

import edu.umn.biomedicus.rtf.exc.EndOfFileException;
import edu.umn.biomedicus.rtf.exc.InvalidKeywordException;
import edu.umn.biomedicus.rtf.exc.InvalidParameterException;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.CharBuffer;
import java.nio.charset.CharsetDecoder;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.Map;

/**
 * Class responsible for parsing an RTF document.
 */
public class RtfParser {
  public static final int KEYWORD_MAX = 32;

  public static final int PARAMETER_MAX = 10;

  private final Map<String, KeywordAction> keywordActionMap;

  private final RtfState initialState;

  private final ByteBuffer bb = ByteBuffer.allocate(1);

  private final CharBuffer cb = CharBuffer.allocate(1);

  private final Deque<RtfState> stateStack = new ArrayDeque<>();

  public RtfParser(Map<String, KeywordAction> keywordActionMap, RtfState initialState) {
    this.keywordActionMap = keywordActionMap;
    this.initialState = initialState;
  }

  public void parseRtf(RtfSource source, RtfSink sink) throws IOException {
    try {
      RtfState state = initialState.copy();
      while (true) {
        int index = source.getIndex();
        int b = source.read();
        if (b == -1) {
          break;
        }
        switch (b) {
          case '{':
            if (state.getCharactersToSkip() > 0) {
              state.setCharactersToSkip(0);
            }
            stateStack.addFirst(state);
            state = state.copy();
            break;
          case '}':
            if (state.getCharactersToSkip() > 0) {
              state.setCharactersToSkip(0);
            }
            state = stateStack.removeFirst();
            if (stateStack.size() == 0) {
              stateStack.addFirst(state);
              state = state.copy();
            }
            break;
          case '\\':
            if (!state.isSkippingDestination()) {
              KeywordAction keywordAction = parseKeyword(index, source);
              if (state.isSkipDestinationIfUnknown()) {
                state.setSkipDestinationIfUnknown(false);
                if (!keywordAction.isKnown()) {
                  state.setSkippingDestination(true);
                }
              }
              keywordAction.executeAction(state, source, sink);
            }
            break;
          case '\n':
          case '\r':
          case 0:
            break;
          default:
            int charactersToSkip = state.getCharactersToSkip();
            if (charactersToSkip > 0) {
              state.setCharactersToSkip(charactersToSkip - 1);
              break;
            }
            if (!state.isSkippingDestination() && state.getPropertyValue("CharacterFormatting", "Hidden") == 0) {
              cb.clear();
              bb.clear();
              bb.put((byte) b);
              bb.rewind();
              CharsetDecoder decoder = state.getDecoder();
              decoder.reset();
              CharBuffer cb = decoder.decode(bb);
              sink.writeCharacter(state.getDestination(), cb.get(), index, source.getIndex());
              break;
            }
        }
      }
    } catch (Exception e) {
      sink.fatalError(e);
      throw e;
    }
  }

  KeywordAction parseKeyword(int index, RtfSource rtfSource) throws IOException {
    int ch = rtfSource.read();
    Integer parameter = null;
    if (ch == -1) {
      throw new EndOfFileException();
    }
    String controlWord;
    if (!Character.isAlphabetic(ch)) {
      controlWord = String.valueOf((char) ch);
      ch = rtfSource.read();
    } else {
      StringBuilder controlWordBuilder = new StringBuilder(KEYWORD_MAX);
      do {
        controlWordBuilder.append((char) ch);
        ch = rtfSource.read();
      } while (controlWordBuilder.length() <= KEYWORD_MAX + 1 && Character.isAlphabetic(ch));
      controlWord = controlWordBuilder.toString();
      if (controlWord.length() > KEYWORD_MAX) {
        throw new InvalidKeywordException("Keyword control word too long: " + controlWord);
      }

      boolean parameterIsNegative = false;

      if (ch == '-') {
        parameterIsNegative = true;
        ch = rtfSource.read();
      }

      if (Character.isDigit(ch)) {
        StringBuilder parameterBuilder = new StringBuilder(PARAMETER_MAX);
        do {
          parameterBuilder.append((char) ch);
          ch = rtfSource.read();
        } while (parameterBuilder.length() <= PARAMETER_MAX + 1 && Character.isDigit(ch));
        String parameterString = parameterBuilder.toString();
        if (parameterString.length() > PARAMETER_MAX) {
          throw new InvalidParameterException("Keyword parameter too long: " + parameterString);
        }
        try {
          parameter = (parameterIsNegative ? -1 : 1) * Integer.parseUnsignedInt(parameterString);
        } catch (NumberFormatException e) {
          throw new InvalidParameterException(
              "Unable to parse parameter into integer: " + parameterString
          );
        }
      }
    }

    if (ch != ' ') {
      rtfSource.unread();
    }

    KeywordAction keywordAction = keywordActionMap.get(controlWord);

    if (keywordAction != null) {
      keywordAction = keywordAction.copy();
    } else {
      keywordAction = new UnknownKeywordAction();
    }

    keywordAction.setControlWord(controlWord);
    keywordAction.setParameter(parameter);
    keywordAction.setBegin(index);
    keywordAction.setEnd(rtfSource.getIndex());

    return keywordAction;
  }
}
