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

package edu.umn.biomedicus.common.data;

import edu.umn.biomedicus.common.exc.DataFilesException;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Accessor for Biomedicus data files.
 */
public class DataFiles {
  private final Path dataPath;

  /**
   * Creates a {@code DataFiles} object for retrieving paths to data.
   */
  public DataFiles() {
    String biomedicusData = System.getenv("BIOMEDICUS_DATA");
    if (biomedicusData == null) {
      throw new DataFilesException("BIOMEDICUS_DATA environment variable is not set");
    }
    dataPath = Paths.get(biomedicusData);
    if (Files.notExists(dataPath) || !Files.isDirectory(dataPath)) {
      throw new DataFilesException("No directory at BIOMEDICUS_DATA path: " + dataPath.toString());
    }
  }

  /**
   * Retrieves a data file from a relative path.
   *
   * @param relativePath The relative path to the data.
   *
   * @return path to the data file
   */
  public Path getDataFile(String relativePath) {
    return getDataFile(Paths.get(relativePath));
  }

  /**
   * Retrieves a data file from a relative path.
   *
   * @param relativePath The relative path to the data
   * @return path to the data file.
   */
  public Path getDataFile(Path relativePath) {
    if (relativePath.isAbsolute()) {
      return relativePath;
    }
    return dataPath.resolve(relativePath);
  }
}
