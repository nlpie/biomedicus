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
    return dataPath.resolve(relativePath);
  }
}
