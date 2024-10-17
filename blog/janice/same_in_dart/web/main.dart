import 'dart:html';
import 'dart:async';

void main() {
  DivElement myDiv = window.document.querySelector("div#output") as DivElement;
  print("myDiv: $myDiv");
  myDiv.onClick.listen((Event event) {
    print("div clicked. event=$event");
  });

  for (var i = 0; i <= 2; i++) {
    String imgSrc = "./imgs/aha/" + i.toString() + ".png";
    ImageElement myimg = new ImageElement(src: imgSrc, width: 800, height: 400);
    myimg.className = "mySlides";
    myDiv.append(myimg);
  }

  const timeout = const Duration(seconds: 3);
  Timer slideShow() {
    return new Timer.periodic(timeout, handleTimeout);
  }

  slideShow();
}

void handleTimeout(Timer timer) {
  // callback function
  print("handleTimeout called");
  List<Node> imgs = document.getElementsByClassName("mySlides");
  print("imgs: $imgs");

  for (var i = 0; i < imgs.length; i++) {
    ImageElement myImgNode = imgs[i] as ImageElement; //casting
    print("myImgNode: $myImgNode");

    // The following illegal case would produce:
    // runTime error:: Uncaught Error: Expected a value of type 'DivElement', but got one of type 'ImageElement'
    // dartanalyzer web/main.dart :: reports no issue
    // dartdevc -o output.js web/main.dart :: reports no issue
    // dart2js -m --out=output-prod.js web/main.dart :: reports no issue
    // DivElement tryCastToDiv = imgs[i] as DivElement;
    // print("tryCastToDiv: $tryCastToDiv");
  }
}
