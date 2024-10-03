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

package edu.umn.biomedicus.rtf.reader;

import org.jetbrains.annotations.Nullable;

import java.io.IOException;

/**
 * Interface for a keyword action, which performs some kind of manipulation of the state when a
 * keyword is encountered in the RTF document.
 */
public interface KeywordAction {
  void executeAction(RtfState state, RtfSource source, RtfSink sink) throws IOException;

  KeywordAction copy();

  int getStartIndex();

  void setBegin(int begin);

  int getEnd();

  void setEnd(int end);

  int getParameter();

  void setParameter(@Nullable Integer parameter);

  boolean hasParameter();

  String getControlWord();

  void setControlWord(String controlWord);

  boolean isKnown();
}
