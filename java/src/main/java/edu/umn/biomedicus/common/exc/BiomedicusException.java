package edu.umn.biomedicus.common.exc;

public class BiomedicusException extends RuntimeException {
  public BiomedicusException() {
    super();
  }

  public BiomedicusException(String message) {
    super(message);
  }

  public BiomedicusException(String message, Throwable cause) {
    super(message, cause);
  }

  public BiomedicusException(Throwable cause) {
    super(cause);
  }

  protected BiomedicusException(String message, Throwable cause, boolean enableSuppression, boolean writableStackTrace) {
    super(message, cause, enableSuppression, writableStackTrace);
  }
}
