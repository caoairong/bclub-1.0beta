#!/usr/bin/env python
# -*- coding: utf-8 -*-
# **************************************************************************
# Copyright © 2016 jianglin
# File Name: views.py
# Author: jianglin
# Email: xiyang0807@gmail.com
# Created: 2016-12-15 22:07:39 (CST)
# Last Update: 星期日 2018-02-11 15:07:05 (CST)
#          By:
# Description:
# **************************************************************************
from flask import Markup, redirect, render_template, request, url_for, current_app
from flask_babelex import gettext as _
from flask_login import current_user, login_required

from flask_auth.form import form_validate
from flask_auth.response import HTTPResponse
from forums.api.forms import (CollectForm, ReplyForm, TopicForm,
                              collect_error_callback, error_callback,
                              form_board)
from forums.api.forums.models import Board
from forums.api.tag.models import Tags
from forums.api.utils import gen_topic_filter, gen_topic_orderby
from forums.common.serializer import Serializer
from forums.common.utils import gen_filter_dict, gen_order_by
from forums.common.views import BaseMethodView as MethodView
from forums.common.views import IsAuthMethodView, IsConfirmedMethodView
from forums.jinja import safe_markdown

from .models import Reply, Topic
from .permissions import (like_permission, reply_list_permission,
                          reply_permission, topic_list_permission,
                          topic_permission, edit_permission)
from forums.api.message.models import MessageClient
from forums.func import get_json, object_as_dict, time_diff
from forums.api.user.models import User
from forums.api.upload.views import GetPhotoView


class TopicAskView(IsConfirmedMethodView):
    def get(self):
        boardId = request.args.get('boardId', type=int)
        form = form_board()
        if boardId is not None:
            form.category.data = boardId
        data = {'title': _('Ask - '), 'form': form}
        return render_template('topic/ask.html', **data)


class TopicEditView(IsConfirmedMethodView):
    decorators = (edit_permission, )

    def get(self, topicId):
        topic = Topic.query.filter_by(id=topicId).first_or_404()
        form = form_board()
        form.title.data = topic.title
        form.category.data = topic.board_id
        form.tags.data = ','.join([tag.name for tag in topic.tags])
        form.content.data = topic.content
        data = {'title': _('Edit -'), 'form': form, 'topic': topic}
        return render_template('topic/edit.html', **data)


class TopicPreviewView(IsConfirmedMethodView):
    @login_required
    def post(self):
        post_data = request.data
        content_type = post_data.pop('content_type', None)
        content = post_data.pop('content', None)
        if content_type == Topic.CONTENT_TYPE_MARKDOWN:
            return safe_markdown(content)
        return content


class TopicListView(MethodView):
    #decorators = (topic_list_permission, )

    def get(self):
        query_dict = request.data
        #page, number = self.page_info
        keys = ['title']
        # order_by = gen_order_by(query_dict, keys)
        # filter_dict = gen_filter_dict(query_dict, keys)
        order_by = gen_topic_orderby(query_dict, keys)
        filter_dict = gen_topic_filter(query_dict, keys)
        title = _('All Topics')
        if request.path.endswith('good'):
            filter_dict.update(is_good=True)
            title = _('Good Topics')
        elif request.path.endswith('top'):
            filter_dict.update(is_bad=True)
            title = _('bad Topics')
        topics = Topic.query.filter_by(
            **filter_dict).order_by(*order_by).all()#.paginate(page, number, True)
        topic = []
        for i in topics:
            user = User.query.filter_by(id=i.author_id).first()
            diff_time = time_diff(i.updated_at)
            i.created_at = str(i.created_at)
            i.updated_at = str(i.updated_at)
            topics_data=object_as_dict(i)
            topics_data['author']=user.username
            topics_data['diff_time']=diff_time
            if user.avatar:
                topics_data['avatar']=user.avatar
            else:
                topics_data['avatar']='http://'+current_app.config['SERVER_NAME']+'/{}/avatar'.format(user.username)
            topic.append(topics_data)
        data = {'classification': title, 'topics': topic}
        return get_json(1,'文章列表', data)
        #return render_template('topic/topic_list.html', **data)

    #@form_validate(form_board, error=error_callback, f='')
    def post(self):
        #user = request.user
        #print(1111111111111111)
        form = TopicForm()
        post_data = form.data
        #print(post_data)
        title = post_data.pop('title', None)
        content = post_data.pop('content', None)
        #tags = post_data.pop('tags', None)
        content_type = post_data.pop('content_type', None)
        token = post_data.pop('token', None)
        #board = post_data.pop('category', None)
        topic = Topic(
            title=title,
            content=content,
            content_type=content_type,
            token = token)
            #board_id=int(board))
        #tags = tags.split(',')
        #topic_tags = []
        #for tag in tags:
        #    tag = tag.strip()
        #    topic_tag = Tags.query.filter_by(name=tag).first()
        #    if topic_tag is None:
        #        topic_tag = Tags(name=tag, description=tag)
        #        topic_tag.save()
        #    topic_tags.append(topic_tag)
        #topic.tags = topic_tags
        topic.author = User.query.filter_by(id=1).first()
        #topic.author = user
        topic.save()
        # count
        #topic.board.topic_count = 1
        #topic.board.post_count = 1
        #topic.author.topic_count = 1
        #topic.reply_count = 1
        return get_json(1, '发表成功', {})
        #return redirect(url_for('topic.topic', topicId=topic.id))

class TopicView(MethodView):
    decorators = (topic_permission, )

    def get(self, topicId):
        #form = ReplyForm()
        query_dict = request.data
        topic = Topic.query.filter_by(id=topicId).first_or_404()
        #page, number = self.page_info
        keys = ['title']
        order_by = gen_order_by(query_dict, keys)
        filter_dict = gen_filter_dict(query_dict, keys)
        replies = topic.replies.filter_by(
            **filter_dict).order_by(*order_by).all()#.paginate(page, number, True)
        replies=[str(i) for i in replies]
        topic.read_count = 1
        topic = object_as_dict(topic)
        user = User.query.filter_by(id=topic['author_id']).first()
        topic['author'] = user.username
        if user.avatar:
            topic['avatar']=user.avatar
        else:
            topic['avatar']=current_app.config['SERVER_NAME']+'/{}/avatar'.format(user.username)
        data = {
            #'title': topic['title'],
            #'form': object_as_dict(form),
            'topic': topic,
            'replies': replies
        }
        #topic.read_count = 1
        return get_json(1,'文章详情',data)
        #return render_template('topic/topic.html', **data)

    @form_validate(form_board)
    def put(self, topicId):
        form = form_board()
        post_data = form.data
        topic = Topic.query.filter_by(id=topicId).first_or_404()
        title = post_data.pop('title', None)
        content = post_data.pop('content', None)
        content_type = post_data.pop('content_type', None)
        category = post_data.pop('category', None)
        if title is not None:
            topic.title = title
        if content is not None:
            topic.content = content
        if content_type is not None:
            topic.content_type = content_type
        if category is not None:
            topic.board_id = int(category)
        topic.save()
        return HTTPResponse(HTTPResponse.NORMAL_STATUS).to_response()


class ReplyListView(MethodView):
    #decorators = (reply_list_permission, )

    #@form_validate(ReplyForm, error=error_callback, f='')
    def post(self, topicId):
        topic = Topic.query.filter_by(id=topicId).first_or_404()
        post_data = request.data
        #user = request.user
        content = post_data.pop('content', None)
        reply = Reply(content=content, topic_id=topic.id)
        #reply.author = user
        reply.author = User.query.filter_by(id=1).first()
        #print(reply)
        reply.save()
        # notice
        #MessageClient.topic(reply)
        # count
        #topic.board.post_count = 1
        reply.author.reply_count = 1
        return get_json(1,'评论成功',{})
        #return redirect(url_for('topic.topic', topicId=topic.id))


class ReplyView(MethodView):

    decorators = (reply_permission, )

    def put(self, replyId):
        post_data = request.data
        reply = Reply.query.filter_by(id=replyId).first_or_404()
        content = post_data.pop('content', None)
        if content is not None:
            reply.content = content
        reply.save()
        return HTTPResponse(HTTPResponse.NORMAL_STATUS).to_response()

    def delete(self, replyId):
        reply = Reply.query.filter_by(id=replyId).first_or_404()
        reply.delete()
        return HTTPResponse(HTTPResponse.NORMAL_STATUS).to_response()


class LikeView(MethodView):

    decorators = (like_permission, )

    def post(self, replyId):
        user = request.user
        reply = Reply.query.filter_by(id=replyId).first_or_404()
        reply.likers.append(user)
        reply.save()
        MessageClient.like(reply)
        serializer = Serializer(reply, many=False)
        return HTTPResponse(
            HTTPResponse.NORMAL_STATUS, data=serializer.data).to_response()

    def delete(self, replyId):
        user = request.user
        reply = Reply.query.filter_by(id=replyId).first_or_404()
        reply.likers.remove(user)
        reply.save()
        serializer = Serializer(reply, many=False)
        return HTTPResponse(
            HTTPResponse.NORMAL_STATUS, data=serializer.data).to_response()