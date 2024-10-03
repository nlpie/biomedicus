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

package edu.umn.biomedicus.normalization;

import org.jetbrains.annotations.Nullable;
import org.rocksdb.*;

import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;

/**
 * Normalizer model which uses RocksDB as a backing map.
 */
public class RocksDBNormalizerModel implements NormalizerModel {

  private final RocksDB db;

  public static RocksDBNormalizerModel loadModel(Path dbPath) {
    return new RocksDBNormalizerModel(dbPath);
  }

  RocksDBNormalizerModel(Path dbPath) {
    RocksDB.loadLibrary();

    try (Options options = new Options()) {
      options.setInfoLogLevel(InfoLogLevel.ERROR_LEVEL);
      db = RocksDB.openReadOnly(options, dbPath.toString());
    } catch (RocksDBException e) {
      throw new RuntimeException(e);
    }
  }

  @Nullable
  @Override
  public String get(@Nullable TermPos termPos) {
    if (termPos == null) {
      return null;
    }
    byte[] key = termPos.getBytes();
    try {
      byte[] bytes = db.get(key);
      return bytes == null ? null : new String(bytes, StandardCharsets.UTF_8);
    } catch (RocksDBException e) {
      throw new RuntimeException(e);
    }
  }

  NormalizerModel inMemory(boolean inMemory) {
    if (!inMemory) {
      return this;
    }

    Map<TermPos, String> map = new HashMap<>();
    try (RocksIterator rocksIterator = db.newIterator()) {
      rocksIterator.seekToFirst();
      while (rocksIterator.isValid()) {
        TermPos termPos = new TermPos(rocksIterator.key());
        String termString = new String(rocksIterator.value(), StandardCharsets.UTF_8);
        map.put(termPos, termString);
        rocksIterator.next();
      }
    }

    return new HashNormalizerModel(map);
  }

  @Override
  public void close() throws Exception {
    db.close();
  }
}
