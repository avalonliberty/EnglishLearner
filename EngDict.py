#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jul  6 10:27:55 2019

@author: avalon
"""
import warnings
import sys
import requests
import pymongo
from datetime import date
from bs4 import BeautifulSoup



class EngDictionary(object):
    '''
    '''
    import warnings

    def __init__(self):
        self.word = ""

    def fit(self, vocabulary):
        self.word = vocabulary

    def look_up(self):
        '''
        '''
        query = "https://www.collinsdictionary.com/us/dictionary/english/"
        checked_url = query + self.word
        word_holder = {"word" : self.word,
                       "content" : [],
                       "day" : 1,
                       "insert_date" : str(date.today())}
        raw_text = requests.get(checked_url).text
        parsed_content = BeautifulSoup(raw_text, "html.parser")
        #self.__suggest_word(self.word, parsed_content)
        try:
            words_section = parsed_content.find("div", {"class" : "content definitions cobuild am"})
            def_section = words_section.findAll("div", {"class" : "hom"})
            for word_content in def_section:
                if word_content.find("div", {"class" : "def"}):
                    main_holder = {}
                    content_holder = {}
                    sentence_holder = []
                    content_holder["pos"] = word_content.find("span", {"class" : "pos"}).text
                    content_holder["definition"] = word_content.find("div", {"class" : "def"}).text.replace("\n", "")

                    example_section = word_content.findAll("div", {"class" : "cit type-example"})

                    for sentence in example_section:
                        cleaned_text = sentence.text.replace("\n", " ").strip()
                        sentence_holder.append(cleaned_text)


                    main_holder["def"] = content_holder
                    main_holder["example"] = sentence_holder
                    word_holder["content"].append(main_holder)
                else:
                    continue
            return word_holder
        except AttributeError:
            query = "https://www.collinsdictionary.com/us/spellcheck/english?q="
            checked_url = query + self.word
            raw_text = requests.get(checked_url).text
            parsed_content = BeautifulSoup(raw_text, "html.parser")
            suggestion_table = parsed_content.find("div", {"class" : "suggested_words"})
            suggestion_list = [suggestion.text for suggestion in suggestion_table.findAll("li")]
            buffer = "Do you mean\n"
            counter = 0
            for word in suggestion_list:
                buffer += word.ljust(15)
                counter += 1
                if counter == 2:
                    buffer += "\n"
                    counter = 0
            return buffer
