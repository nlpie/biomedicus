package edu.umn.biomedicus.common.tokenization;

import edu.umn.nlpnewt.model.GenericLabel;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.assertEquals;

class WhitespaceTokenizerTest {
  @Test
  void testWhitespaceTokenizer() {
    String text = "The quick-brown-fox jumps over the lazy dog. He's still a good boy, though.";
    List<GenericLabel> tokenize = WhitespaceTokenizer.tokenize(text);
    List<String> list = tokenize.stream().map(t -> t.coveredText(text).toString()).collect(Collectors.toList());
    assertEquals(Arrays.asList("The", "quick-brown-fox", "jumps", "over", "the", "lazy", "dog.",
        "He's", "still", "a", "good", "boy,", "though."), list);
  }
}
