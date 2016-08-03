#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# @file: railgun/website/forms.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# This file is released under BSD 2-clause license.

import json

from flask_wtf import Form
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, SelectField, BooleanField,DateField,SubmitField,TextAreaField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from flask_pagedown import PageDown
from flask_pagedown.fields import PageDownField
from wtforms.widgets import TextArea
from wtforms.validators import (DataRequired, Length, Email, InputRequired,EqualTo, Regexp, URL, ValidationError,Required)
from babel import UnknownLocaleError
from pytz import timezone, UnknownTimeZoneError
from flask.ext.babel import Locale, lazy_gettext as _
from flask.ext.login import current_user
from config import HOMEWORK_TYPE_SET
from pymongo import MongoClient

from .models import User
from .context import db, app
from .i18n import list_locales
from .utility import format_size
from .userauth import has_user


class MultiRowsTextArea(TextArea):
    """HTML Text Area whose `rows` attribute can be set when define the
    :class:`~flask_wtf.Form` schema.

    :param rows: The `rows` attribute in HTML tag.
    :type rows: :class:`int`
    """

    def __init__(self, rows=10):
        super(MultiRowsTextArea, self).__init__()
        self.rows = rows

    def __call__(self, field, **kwargs):
        kwargs.setdefault('rows', self.rows)
        return super(MultiRowsTextArea, self).__call__(field, **kwargs)

class BaseForm(Form):

    def __init__(self, *args, **kwargs):
        super(BaseForm, self).__init__(*args, **kwargs)


def _MakeClassChoices():
    result = [(i,i) for i in HOMEWORK_TYPE_SET ]
    return result

def _MakeCourseChoices():
    courses = app.config['COURSE_COLLECTION'].find()
    course_set = []
    for course in courses:
        course_set.append((course['name'],course['name']))
    return course_set

class AddcourseForm(BaseForm):
    name = StringField(_('Course name'),validators=[DataRequired(message=_("Course name can't be blank"))])


class Course_Choose_Form(BaseForm):
    def query_factory():
        courses = app.config['COURSE_COLLECTION'].find()
        course_set = []
        for course in courses:
            course_set.append(course['name'])
        return course_set

    #return [r.name for r in db.session.query(Script).all()]
    
    def get_pk(obj):
        return obj
    
    name = QuerySelectField(label = _('Course Choose'),validators=[DataRequired(message=_("Please choose course first."))],query_factory=query_factory, get_pk=get_pk)


class AddproblemForm(BaseForm):
    type = SelectField(_('Homework type'),choices=_MakeClassChoices(),validators=[DataRequired(message=_("Homework type can't be blank")),])

    name = StringField(_('Homework English name'),validators=[DataRequired(message=_("Homework English name can't be blank")),
        Regexp('^[A-Za-z0-9_]*$', message=_("Only letters, digits and '_' can appear in Homework English name.")),
        Length(min=1, max=32, message=_("Homework English name must be no shorter than 1 ""and no longer than 32 characters"))])

    ch_name = StringField(_('Homework Chinese name'),validators=
        [DataRequired(message=_("Homework Chinese name can't be blank"))])

    word_desc = StringField(_('Homework concise description'),validators=[
        DataRequired(message=_("Homework concise description can't be blank")),
        Length(min=1, max=45, message=_("Homework concise description must be no shorter than 1 ""and no longer than 45 characters"))])
        
    code_file = FileField(_('Please choose an archive to submit:'),
    validators=[FileRequired(),FileAllowed(['zip'],message=_('Only these file formats are accepted: zip'))
    ])

class User_ClassForm(BaseForm):
    user_data = TextAreaField(_('User_Class data'))
    
class CreateUserForm(BaseForm):
    """The basic form to create a new user account.
    This form is used in :func:`~railgun.website.admin.adduser` view directly
    without modification.  Moreover, it is also derived by :class:`SignupForm`
    as a registration form for new users.
    """

    #: The username text input.  Valid pattern is ``[A-Za-z0-9_]``,
    #: minimum length is 3, and maximum length is 32.
    name = StringField(_('Username'), validators=[
        Regexp('^[A-Za-z0-9_]*$', message=_("Only letters, digits and '_' can "
                                            "appear in username.")),
        DataRequired(message=_("Username can't be blank")),
        Length(min=3, max=32, message=_("Username must be no shorter than 3 "
                                        "and no longer than 32 characters")),
    ])
    #: The password text input.  Minimum length is 7, and maximum length is 32.
    #: It must be equal to :attr:`confirm`.
    password = PasswordField(_('Password'), validators=[
        InputRequired(message=_("Password can't be blank")),
        EqualTo('confirm', message=_("Passwords must match")),
        Length(min=7, max=32, message=_("Password must be no shorter than 7 "
                                        "and no longer than 32 characters")),
    ])
    #: The password confirm text input.
    confirm = PasswordField(_('Confirm your password'))

    def validate_name(form, field):
        """Extra validation that the username has not been taken."""
        if has_user(field.data):
            raise ValidationError(_('Username already taken'))


class SignupForm(CreateUserForm):
    """The form for anonymous users to create a new account.  Derived from
    :class:`CreateUserForm`, used in :func:`~railgun.website.views.signup`.
    """

    #: The email address text input.  Input text must be a valid email
    #: address, and the maximum length is 80.
    email = StringField(_('Email Address'), validators=[
        DataRequired(message=_("Email can't be blank")),
        Email(message=_("Email is invalid")),
        Length(message=_("Email must be no longer than 80 characters"),
               max=80),
    ])

    def validate_email(form, field):
        """Extra validation that the email has not been taken."""
        if has_user(field.data):
            raise ValidationError(_('Email already taken'))


class SigninForm(BaseForm):
    """The form for users to sign in.
    Used in :func:`~railgun.website.views.signin`.
    """

    #: Username or email address text input.
    login = StringField(_('Username or Email'), validators=[InputRequired()])
    #: Password text input.
    password = PasswordField(_('Password'), validators=[InputRequired()])
    #: The checkbox indicating whether to make the user session persistent.
    #: A persistent session can live alive even after the user quits his or
    #: her web browser.
    remember = BooleanField(_('Remember me?'))


class ReAuthenticateForm(BaseForm):
    """The form for users to re-validate themselves by enter their passwords.
    Used in :func:`~railgun.website.views.reauthenticate`.
    """

    #: Password text input.
    password = PasswordField(_('Password'), validators=[InputRequired()])


def _MakeLocaleChoices():
    """Prepare data of available locales for :class:`~wtforms.SelectField`."""
    return [(str(l), l.display_name) for l in list_locales()]


class Problem_edit_Form(BaseForm):
    '''The form is used to modify the problem message'''

    desc = PageDownField(_('Description'))

    solve = PageDownField(_('Solution'))

    code_file = FileField(_('Please choose an archive to submit:'),validators=[FileAllowed(['zip'],message=_('Only these file formats are accepted: zip'))
                                  ])






class ProfileForm(BaseForm):
    """The form to edit a user's profile.
    Used in :func:`~railgun.website.views.profile_edit` directly, and is
    derived by :class:`AdminUserEditForm` for admins to edit user profiles.

    Some fields in this form should be disabled, since users from third-party
    authentication providers may not allow to change these fields.
    You may refer to :class:`railgun.website.userauth.AuthProvider` for more
    details.
    """

    #: The email address text input.  Input text must be a valid email
    #: address, and the maximum length is 80.
    email = StringField(_('Email Address'), validators=[
        DataRequired(message=_("Email can't be blank")),
        Email(message=_("Email is invalid")),
        Length(message=_("Email must be no longer than 80 characters"),
               max=80),
    ])
    #: The password text input.  Minimum length is 7, and maximum length is 32.
    #: It must be equal to :attr:`confirm`.
    password = PasswordField(_('Password'), validators=[
        EqualTo('confirm', message=_("Passwords must match")),
    ])
    #: The password confirm text input.
    confirm = PasswordField(_('Confirm your password'))
    
    #: The given name text input.  Maximum length is 64.
    given_name = StringField(_('Given Name'), validators=[
        Length(max=64, message=_("Given name must be no longer than 64 "
                                 "characters")),
    ])
    #: The family name text input.  Maximum length is 64.
    family_name = StringField(_('Family Name'), validators=[
        Length(max=64, message=_("Family name must be no longer than 64 "
                                 "characters")),
    ])

    #: The language select field input.  Only the languages with translations
    #: installed are listed here.
    locale = SelectField(
        _('Speaking Language'),
        choices=_MakeLocaleChoices(),
        validators=[
            DataRequired(message=_("Speaking language can't be blank")),
        ]
    )
    #: The class the students belong to
    
    '''
    student_class = SelectField(
                                _('Grade and Class'),
                                choices=_MakeClassChoices(),
                                validators=[
                        DataRequired(message=_("Speaking language can't be blank")),
                                ]
    )
    '''
    
    #: The timezone text input.
    timezone = StringField(_('Timezone'), validators=[
        DataRequired(message=_("Timezone can't be blank")),
    ])

    @property
    def the_user(self):
        """Get the user object associated with this form.  Default is
        :data:`~flask.ext.login.current_user`.
        """
        return getattr(self, '_m_the_user', current_user)

    @the_user.setter
    def the_user(self, value):
        """Set the user object associated with this form."""
        self._m_the_user = value

    # Special inline validators on email and password
    def validate_email(form, field):
        """Extra validation that the email has not been taken.

        .. note::

            Email addresses ends with ``config.EXAMPLE_USER_EMAIL_SUFFIX``
            is not allowed.

        .. note::

            We need :attr:`the_user` to get associated user id, since we
            should allow the user to keep his or her email not changed,
            we then allow the user with same user id in the database
            has the same email address.
        """
        if (db.session.query(User).
                filter(User.email == field.data).
                filter(User.id != form.the_user.id).
                count()):
            raise ValidationError(_('Email already taken'))
        if (field.data and
                field.data.endswith(app.config['EXAMPLE_USER_EMAIL_SUFFIX'])):
            raise ValidationError(_('You should provide a valid email.'))

    def validate_password(form, field):
        """Validate whether the password length is within 7 and 32 characters.

        We move the validations of password from general validators to
        customized method, in that we may allow the user to keep the password
        input empty, which means to keep password unchanged.
        """
        pwd_len = len(field.data)
        if field.data and (pwd_len < 7 or pwd_len > 32):
            raise ValidationError(
                _("Password must be no shorter than 7 and no longer than "
                  "32 characters")
            )

    def validate_locale(form, field):
        """Validate whether the user provided locale is a valid locale."""
        try:
            Locale(field.data)
        except UnknownLocaleError:
            raise ValidationError(
                _("Please select a valid locale from above."))

    def validate_timezone(form, field):
        """Validate whether the user provided timezone is a valid timezone.
        Lists of valid timezones can be found on `Wikipedia
        <http://en.wikipedia.org/wiki/List_of_tz_database_time_zones>`_
        """
        try:
            timezone(field.data)
        except UnknownTimeZoneError:
            raise ValidationError(_("Please enter a valid timezone."))

class AdminUserEditForm(ProfileForm):
    """Derived from :class:`ProfileForm`, allow admins to edit a user's
    profile.  The only additional widget is :attr:`is_admin`.
    Used in :func:`~railgun.website.admin.user_edit`, where
    :attr:`~ProfileForm.the_user` would be set.
    """

    #: Checkbox input representing whether the user is an administrator.
    is_admin = BooleanField(_('Is administrator?'))


class UploadHandinForm(BaseForm):
    """The form for users to upload archive files as submissions."""

    #: File upload input.  Only archive files are allowed.
    handin = FileField(
        _('Please choose an archive to submit:'),
        validators=[
            FileRequired(),
            FileAllowed(
                ['rar', 'zip', 'tar', 'tgz', 'tbz', 'gz', 'bz2'],
                message=_('Only these file formats are accepted: '
                          'rar, zip, tar, tar.gz, tgz, tar.bz2, tbz')
            )
        ])

    def validate_handin(form, field):
        """Extra validation on :attr:`handin` that the uploaded file
        must not be larger than ``config.MAX_SUBMISSION_SIZE``.
        """
        if not field.data:
            return
        # try to get the file size of uploaded file
        field.data.stream.seek(0, 2)
        fsize = field.data.stream.tell()
        field.data.stream.seek(0)
        if fsize > app.config['MAX_SUBMISSION_SIZE']:
            raise ValidationError(_(
                "Archive files larger than %(size)s is not allowed.",
                size=format_size(app.config['MAX_SUBMISSION_SIZE'])
            ))


class AddressHandinForm(BaseForm):
    """The form for users to give url addresses as submissions."""

    #: The url address text input.  Must be valid url addresses.
    address = StringField(
        _('Please enter your API address:'),
        validators=[
            InputRequired(),
            URL(message=_('Please input a valid url address!'),
                require_tld=False)
        ])


class CsvHandinForm(BaseForm):
    """The form for users to give CSV data as submissions."""

    #: The CSV data text area.  Use :class:`MultiRowsTextArea` as the
    #: widget so that `rows` are defined.
    csvdata = StringField(
        _('Csv data:'),
        validators=[InputRequired()],
        widget=MultiRowsTextArea()
    )


class VoteJsonEditForm(BaseForm):
    """The form to edit a vote using JSON source code."""

    json_source = StringField(
        _('Json Source:'),
        validators=[InputRequired()],
        widget=MultiRowsTextArea(rows=24)
    )

    def validate_json_source(form, field):
        """Extract the vote data from JSON source code and and construct
        object representation."""

        if not field.data:
            return
        try:
            obj = json.loads(field.data)
            if not isinstance(obj, dict):
                raise ValidationError(_('Object must be a dictionary.'))

            for k in ('title', 'desc', 'items'):
                if k not in obj:
                    raise ValidationError(
                        _('Field "%(field)s" is required in a vote.',
                          field=k)
                    )
            if 'items' not in obj or not obj['items']:
                raise ValidationError(_('No option is defined for this vote.'))

            for itm in obj['items']:
                for k in ('title', 'desc'):
                    if k not in itm:
                        raise ValidationError(
                            _('Field "%(field)s" is required in an option.',
                              field=k)
                        )
                for k in ('logo', ):
                    if k not in itm:
                        itm[k] = None
        except ValidationError:
            raise
        except Exception:
            raise ValidationError(_('Could not parse the JSON text.'))


class VoteSignupForm(BaseForm):
    """The form to signup a project for the voting."""

    #: File upload input.  Only image files are allowed.
    logo = FileField(
        _('Please upload your logo:'),
        validators=[
            FileAllowed(
                ['jpg', 'png', 'bmp', 'gif'],
                message=_('Only these file formats are accepted: '
                          'jpg, png, bmp, gif')
            )
        ])

    #: The group name input.
    group_name = StringField(_('Group Name'), validators=[
        Length(max=80, message=_("Group name must be no longer than 80 "
                                 "characters")),
        DataRequired(),
    ])

    #: The project name input.
    project_id = SelectField(
        _('Project Name'),
        choices=[
            (idx, name)
            for idx, name in enumerate(app.config['VOTE_PROJECT_NAMES'])
        ],
        coerce=int,
        validators=[InputRequired()],
    )

    #: The description input.
    description = StringField(_('Description'), validators=[
        DataRequired()
    ], widget=MultiRowsTextArea(rows=12))

    def validate_logo(form, field):
        """Extra validation on :attr:`logo` that the uploaded file
        must not be larger than ``config.VOTE_LOGO_MAXIMUM_FILE_SIZE``.
        """
        if not field.data:
            return
        # try to get the file size of uploaded file
        field.data.stream.seek(0, 2)
        fsize = field.data.stream.tell()
        field.data.stream.seek(0)
        if fsize > app.config['VOTE_LOGO_MAXIMUM_FILE_SIZE']:
            raise ValidationError(_(
                "Image files larger than %(size)s is not allowed.",
                size=format_size(app.config['VOTE_LOGO_MAXIMUM_FILE_SIZE'])
            ))
