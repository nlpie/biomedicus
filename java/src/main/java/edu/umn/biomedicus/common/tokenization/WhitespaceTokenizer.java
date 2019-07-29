package edu.umn.biomedicus.common.tokenization;

import edu.umn.nlpnewt.model.GenericLabel;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.NoSuchElementException;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class WhitespaceTokenizer {
  public static final Pattern WHITESPACE_PATTERN = Pattern.compile("\\s++");

  private WhitespaceTokenizer() {
    throw new UnsupportedOperationException();
  }

  public static List<GenericLabel> tokenize(CharSequence text) {
    List<GenericLabel> result = new ArrayList<>();
    Matcher matcher = WHITESPACE_PATTERN.matcher(text);
    int nextBegin = 0;
    while (matcher.find()) {
      GenericLabel token = GenericLabel.createSpan(nextBegin, matcher.start());
      nextBegin = matcher.end();
      if (token.length() > 0) {
        result.add(token);
      }
    }
    if (nextBegin != text.length()) {
      result.add(GenericLabel.createSpan(nextBegin, text.length()));
    }
    return result;
  }
}
