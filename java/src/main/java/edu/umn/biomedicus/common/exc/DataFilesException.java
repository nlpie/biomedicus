package edu.umn.biomedicus.common.exc;

public class DataFilesException extends BiomedicusException {
  public DataFilesException() {
  }

  public DataFilesException(String message) {
    super(message);
  }

  public DataFilesException(String message, Throwable cause) {
    super(message, cause);
  }

  public DataFilesException(Throwable cause) {
    super(cause);
  }

  public DataFilesException(String message, Throwable cause, boolean enableSuppression, boolean writableStackTrace) {
    super(message, cause, enableSuppression, writableStackTrace);
  }
}
