---
layout: default
---

<!-- Present all posts in the blog category, and link to them -->

<script type="text/x-mathjax-config">
MathJax.Hub.Register.StartupHook('TeX Jax Ready', function () {
  MathJax.InputJax.TeX.prefilterHooks.Add(function (data) {
    data.math = data.math.replace(/^% <!\[CDATA\[/, '').replace(/%\]\]>$/, '');
  });
});
</script>
<script type="text/javascript" id="MathJax-script" async src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.6/latest.js"></script>

<p><img src="/images/back2.svg" style="display:block;margin-left:auto;margin-right:auto;border-radius: 8px;width: 100%; height:auto; margin-top:10px; margin-bottom:0px;"></p>

<span style="margin-left: auto;float:right;color: tomato;font-family: sans-serif;font-size: 15px;">
   <img src="./images/klingon.svg" width=26 height=26>
  <a href='iitG_0225.html'>IIT-G presentation</a>
</span>

<ul>
{%- for post in site.categories.blog -%}       
  <p class="post" style="margin-bottom: 10px;">
        <p><h3><a style="float:left">{{ post.title }}</a> <a style="float:right">{{post.date | date: site.ghostly.date_format}}</a> </h3></p>
     	<p><img src="{{ post.image | prepend: site.baseurl }}" style="float:left;border-radius: 8px;max-width: 10%; height:auto; margin-bottom:10px;">
        <h3 style="float:right;max-width:85%">
           {{ post.excerpt | strip_html | truncatewords:25, " ..."}}
            <a href="{{ post.url }}"  style="float:right;">{{ site.ghostly.morebutton }}</a>    </h3>
        </p>    
  </p>
{%- endfor -%}
</ul>