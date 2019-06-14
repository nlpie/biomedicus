/*
 * Copyright 2019 Regents of the University of Minnesota
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
import edu.umn.biomedicus.rtf.exc.RtfReaderException;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.CharBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CoderResult;
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

  private final State initialState;

  public RtfParser(Map<String, KeywordAction> keywordActionMap, State initialState) {
    this.keywordActionMap = keywordActionMap;
    this.initialState = initialState;
  }

  public void parseFile(RtfSource rtfSource, RtfSink rtfSink) throws IOException {
    State currentState = initialState.copy();
    Deque<State> stateStack = new ArrayDeque<>();
    ByteBuffer bb = ByteBuffer.allocate(1);
    CharBuffer cb = CharBuffer.allocate(1);
    while (true) {
      int index = rtfSource.getIndex();
      int b = rtfSource.read();
      if (b == -1) {
        break;
      }
      switch (b) {
        case '{':
          stateStack.addFirst(currentState);
          currentState = currentState.copy();
          break;
        case '}':
          if (stateStack.size() == 0) {
            throw new RtfReaderException("Extra closing brace.");
          }
          currentState = stateStack.removeFirst();
          break;
        case '\\':
          KeywordAction keywordAction = parseKeyword(index, rtfSource);
          try {
            keywordAction.executeAction(currentState, rtfSource, rtfSink);
          } catch (java.io.IOException e) {
            e.printStackTrace();
          }
          break;
        case '\n':
        case '\r':
        case 0:
          break;
        default:
          cb.clear();
          bb.clear();
          bb.put((byte) b);
          CoderResult coderResult = currentState.getDecoder().decode(bb, cb, true);
          if (coderResult.isError()) {
            try {
              coderResult.throwException();
            } catch (CharacterCodingException e) {
              throw new RtfReaderException(e);
            }
          }
          rtfSink.writeCharacter(cb.get(), index, rtfSource.getIndex());
          break;
      }
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
      controlWord = "" + (char) ch;
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
