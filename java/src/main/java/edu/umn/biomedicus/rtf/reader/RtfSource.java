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

import java.io.BufferedInputStream;
import java.io.IOException;
import java.io.InputStream;

public class RtfSource extends InputStream {
  private final BufferedInputStream is;

  private int index;

  public RtfSource(BufferedInputStream bufferedInputStream) {
    is = bufferedInputStream;
    index = 0;
  }

  public int getIndex() {
    return index;
  }

  @Override
  public int read() throws IOException {
    is.mark(1);
    int code = is.read();
    index++;
    return code;
  }

  public void unread() throws IOException {
    is.reset();
    index--;
  }
}
