$("div.img_container").hover(function(){
  console.log("hover");
  $(this).children("div.overlay").css("height", $("div.text").outerHeight());
  //$(this).children("div.overlay").children("div.text").css("width", $("div.overlay").outerWidth());
  console.log($("div.overlay").outerHeight())
  }, function(){
    $(this).children("div.overlay").css("height", "0");
});