---
layout: default
title: "£robl€m$"
---

{%- assign now_s = site.time | date: '%s' | plus: 0 -%}
{%- assign problems = site.categories.problem | concat: site.categories.proj | sort: 'date' | reverse -%}

<style>
/* rules box, open and closed problems share one geometry; the bar color carries the status */
.pb-rules, .pb-item { border-left: 5px solid #B8B8B8; padding: 0.2em 0 0.2em 1em; margin: 0 0 1.8em 0; overflow: hidden; }
.pb-rules { font-size: medium; color: #444; margin-top: 0.5em; margin-bottom: 2.4em; }
.pb-rules p { margin: 0 0 0.7em 0; padding: 0; }
.pb-rules p:last-child { margin-bottom: 0; }
.pb-item.open   { border-left-color: seagreen; }
.pb-item.closed { border-left-color: crimson; }
.pb-item h3 { margin: 0; padding: 0; }
.pb-item h3 a { font-weight: bold; }
.pb-item h3 .pb-date { color: #888; margin-right: 0.8em; }
.pb-item .pb-teaser { margin: 0.3em 0 0 0; padding: 0; }
.pb-st { margin-left: 0.6em; vertical-align: middle; font-family: sans-serif; font-size: 13px; padding: 0.1em 0.5em; border-radius: 4px; border: 1px solid seagreen; color: seagreen; }
</style>

<div class="tex2jax_ignore">
<div class="pb-rules">
<p>Every second week I pose a problem. The solution I judge best is rewarded with <span class="nobr">{{ site.problems.bounty }}</span>, payable via the {{ site.problems.payment }}.</p>
<p>For technical problems, a working apparatus (physical or software-virtual) is needed along with practical usage instructions.
For conceptual problems, I reward the elegant, minimal, succinct, intuitive, practical, jargon-free, leading-further, humble, &ldquo;linear&rdquo; explanation in form of a properly annotated sketch/diagram.
For non-natural-science problems, I reward those stories which come closest to my ideal of a story-telling style which integrates Rand's dichotomic selection of characters with Ernest's raw vocabulary with Thomas' complex syntax with Ian's elements of human surprises and Herbert's vision of how it all combines over eons.</p>
<p>Inquiries, solutions &rarr; <a href="mailto:{{ site.email }}">{{ site.email }}</a></p>
</div>
</div>

{%- for post in problems -%}
{%- assign st = "closed" -%}
{%- if post.categories contains "problem" and post.status != "awarded" and post.status != "closed" -%}
  {%- assign dl_s = post.deadline | date: '%s' | plus: 86399 -%}
  {%- if dl_s >= now_s -%}{%- assign st = "open" -%}{%- endif -%}
{%- endif -%}
{%- assign paras = post.content | split: '<p>' -%}
<div class="pb-item {{ st }}">
  <h3><span class="pb-date">{{ post.date | date: site.ghostly.date_format }}</span><a href="{{ post.url }}">{{ post.title }}</a>
    {%- if st == "open" %}<span class="pb-st">open</span>{% endif -%}
    {%- if post.status == "awarded" and post.solver %} <span class="pb-date">&middot; {{ post.solver }}</span>{% endif %}</h3>
  <p class="pb-teaser">{{ paras[1] | split: '</p>' | first | strip_html | strip | truncatewords: 45, " ..." }}
    <a href="{{ post.url }}">&rarr;</a></p>
</div>
{%- endfor -%}
