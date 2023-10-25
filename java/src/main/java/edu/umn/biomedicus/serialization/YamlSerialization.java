package edu.umn.biomedicus.serialization;

import edu.umn.biomedicus.common.pos.PartOfSpeech;
import edu.umn.biomedicus.common.pos.PartsOfSpeech;
import edu.umn.biomedicus.common.tuples.PosCap;
import edu.umn.biomedicus.concepts.CUI;
import edu.umn.biomedicus.concepts.SUI;
import edu.umn.biomedicus.concepts.TUI;
import org.yaml.snakeyaml.DumperOptions;
import org.yaml.snakeyaml.LoaderOptions;
import org.yaml.snakeyaml.Yaml;
import org.yaml.snakeyaml.constructor.AbstractConstruct;
import org.yaml.snakeyaml.constructor.Constructor;
import org.yaml.snakeyaml.inspector.TagInspector;
import org.yaml.snakeyaml.nodes.Node;
import org.yaml.snakeyaml.nodes.ScalarNode;
import org.yaml.snakeyaml.nodes.Tag;
import org.yaml.snakeyaml.representer.Representer;

/**
 *
 */
public final class YamlSerialization {
  private YamlSerialization() {
    throw new UnsupportedOperationException();
  }

  public static Yaml createYaml() {
    LoaderOptions loaderOptions = new LoaderOptions();
    loaderOptions.setCodePointLimit(15 * 1024 * 1024);
    TagInspector tagInspector = tag -> true;
    loaderOptions.setTagInspector(tagInspector);
    return createYaml(loaderOptions, new DumperOptions());
  }

  public static Yaml createYaml(LoaderOptions loaderOptions, DumperOptions dumperOptions) {
    Representer representer = representer(dumperOptions);
    Constructor constructor = constructor(loaderOptions);
    return new Yaml(constructor, representer, dumperOptions, loaderOptions);
  }

  private static Constructor constructor(LoaderOptions loaderOptions) {
    return new Constructor(loaderOptions) {
      {
        yamlConstructors.put(new Tag("!pc"), new AbstractConstruct() {
          @Override
          public Object construct(Node node) {
            String value = constructScalar((ScalarNode) node);
            boolean isCapitalized = value.charAt(0) == 'C';
            PartOfSpeech partOfSpeech = PartsOfSpeech.forTag(value.substring(1));
            return PosCap.create(partOfSpeech, isCapitalized);
          }
        });
        yamlConstructors.put(new Tag("!pos"), new AbstractConstruct() {
          @Override
          public Object construct(Node node) {
            String value = constructScalar((ScalarNode) node);
            return PartsOfSpeech.forTag(value);
          }
        });
        yamlConstructors.put(new Tag("!cui"), new AbstractConstruct() {
          @Override
          public Object construct(Node node) {
            String val = constructScalar((ScalarNode) node);
            return new CUI(val);
          }
        });
        yamlConstructors.put(new Tag("!tui"), new AbstractConstruct() {
          @Override
          public Object construct(Node node) {
            String val = constructScalar((ScalarNode) node);
            return new TUI(val);
          }
        });
        yamlConstructors.put(new Tag("!sui"), new AbstractConstruct() {
          @Override
          public Object construct(Node node) {
            String val = constructScalar((ScalarNode) node);
            return new SUI(val);
          }
        });
      }
    };
  }

  private static Representer representer(DumperOptions dumperOptions) {
    return new Representer(dumperOptions) {
      {
        representers.put(PosCap.class, o -> {
          PosCap posCap = (PosCap) o;
          String value = (posCap.isCapitalized() ? "C" : 'l') + posCap.getPartOfSpeech().toString();
          return representScalar(new Tag("!pc"), value);
        });
        representers.put(PartOfSpeech.class, o -> {
          PartOfSpeech partOfSpeech = (PartOfSpeech) o;
          String value = partOfSpeech.toString();
          return representScalar(new Tag("!pos"), value);
        });
        representers.put(CUI.class, o -> {
          CUI cui = (CUI) o;
          String value = cui.toString();
          return representScalar(new Tag("!cui"), value);
        });
        representers.put(TUI.class, o -> {
          TUI tui = (TUI) o;
          String value = tui.toString();
          return representScalar(new Tag("!tui"), value);
        });
        representers.put(SUI.class, o -> {
          SUI sui = (SUI) o;
          String value = sui.toString();
          return representScalar(new Tag("!sui"), value);
        });
      }
    };
  }
}
