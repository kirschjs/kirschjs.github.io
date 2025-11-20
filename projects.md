---
layout: default
---

<!-- Present all posts in the blog category, and link to them -->

<ul>
{%- for post in site.categories.proj -%}       
  <p class="post" style="margin-bottom: 40px;">
        <p><h3><a style="float:left">{{ post.title }}</a> <a style="float:right">{{post.date | date: site.ghostly.date_format}}</a> </h3></p>
     	<p><img src="{{ post.image | prepend: site.baseurl }}" style="float:left;border-radius: 8px;max-width: 10%; height:auto; margin-bottom:10px;">
        <h3 style="float:right;max-width:85%">
           {{ post.excerpt | strip_html | truncatewords:25, " ..."}}
            <a href="{{ post.url }}"  style="float:right;">{{ site.ghostly.morebutton }}</a>    </h3>
        </p>    
  </p>
{%- endfor -%}
</ul>