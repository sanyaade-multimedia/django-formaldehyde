from __future__ import unicode_literals
import django
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, Client
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.utils import six

from formaldehyde.conf import settings
from formaldehyde.fieldsets import FieldsetFormMixin
from formaldehyde.readonly import ReadonlyFormMixin
from formaldehyde.whitespace import StripWhitespaceFormMixin


#==============================================================================
class TestFieldsetForm(FieldsetFormMixin, forms.Form):
    first_name = forms.CharField(label='First name', max_length=100)
    middle_name = forms.CharField(label='Middle name', max_length=100)
    last_name = forms.CharField(label='Last name', max_length=100)
    street = forms.CharField(label='Street name', max_length=100)

    class MetaForm:
        fieldsets = (
            (None, {
                'fields': (
                    ('first_name', 'middle_name'),
                    'last_name',
                ),
                'layout': (
                    (4, 6),
                    2
                ),
                'labels': (
                    (1, 1),
                    10
                ),
                'classes': 'form-control'
            }),
            ('Address', {
                'fields': (
                    'street',
                )
            }),
        )

class TestFieldsetModelForm(FieldsetFormMixin, forms.ModelForm):
    class Meta:
        model = ContentType
        fields = "__all__"

class TestFieldsetFormRaises(FieldsetFormMixin):
    pass

class TestReadonlyForm(ReadonlyFormMixin, forms.Form):
    first_name = forms.CharField(label='First name', max_length=100)

class TestReadonlyModelForm(ReadonlyFormMixin, forms.ModelForm):
    class Meta:
        model = ContentType
        fields = "__all__"

class TestWhitespaceForm(StripWhitespaceFormMixin, forms.Form):
    first_name = forms.CharField(label='First name', max_length=100)
    last_name = forms.CharField(label='Last name', max_length=100)

    def full_clean(self):
        self.strip_whitespace_from_data()
        super(TestWhitespaceForm, self).full_clean()

class TestWhitespaceModelForm(StripWhitespaceFormMixin, forms.ModelForm):
    class Meta:
        model = ContentType
        fields = "__all__"

    def full_clean(self):
        self.strip_whitespace_from_data()
        super(TestWhitespaceModelForm, self).full_clean()


#==============================================================================
class FormalehydeTestCase(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def tearDown(self):
        pass

    def test_fieldset_form(self):
        form = TestFieldsetForm()
        fieldsets = form.fieldsets()
        self.assertIsNotNone(fieldsets)

        fieldset01 = six.next(fieldsets)
        self.assertIsNone(fieldset01.legend)
        self.assertEqual(fieldset01.description, '')
        self.assertEqual(fieldset01.classes, 'form-control')

        fieldset01_line01 = six.next(fieldset01)
        fieldset01_line01_field01, fieldset01_line01_layout01, fieldset01_line01_label01 = six.next(fieldset01_line01)
        self.assertEqual('first_name', fieldset01_line01_field01.name)
        self.assertEqual(4, fieldset01_line01_layout01)
        self.assertEqual(1, fieldset01_line01_label01)
        fieldset01_line01_field02, fieldset01_line01_layout02, fieldset01_line01_label02 = six.next(fieldset01_line01)
        self.assertEqual('middle_name', fieldset01_line01_field02.name)
        self.assertEqual(6, fieldset01_line01_layout02)
        self.assertEqual(1, fieldset01_line01_label01)

        fieldset01_line02 = six.next(fieldset01)
        fieldset01_line02_field01, fieldset01_line02_layout01, fieldset01_line02_label01 = six.next(fieldset01_line02)
        self.assertEqual('last_name', fieldset01_line02_field01.name)
        self.assertEqual(2, fieldset01_line02_layout01)
        self.assertEqual(10, fieldset01_line02_label01)

        fieldset02 = six.next(fieldsets)
        self.assertEqual(fieldset02.legend, 'Address')
        self.assertEqual(fieldset02.description, '')
        self.assertEqual(fieldset02.classes, '')

        fieldset02_line01 = six.next(fieldset02)
        fieldset02_line01_field01, fieldset02_line01_layout01, fieldset02_line01_label01 = six.next(fieldset02_line01)
        self.assertEqual('street', fieldset02_line01_field01.name)
        self.assertEqual(settings.DEFAULT_FIELD_COLUMN_SIZE, fieldset02_line01_layout01)
        self.assertEqual(settings.FIRST_LABEL_COLUMN_SIZE, fieldset02_line01_label01)

    def test_fieldset_model_form(self):
        form = TestFieldsetModelForm()
        if form.fieldsets:
            fieldsets = form.fieldsets()
            six.next(fieldsets)

    def test_raises_form(self):
        with self.assertRaises(AssertionError):
            form = TestFieldsetFormRaises()

    def test_readonly_form(self):
        form = TestReadonlyForm()
        form.set_readonly(True)
        self.assertTrue(form.fields['first_name'].is_readonly)
        form.set_readonly(False)
        self.assertFalse(form.fields['first_name'].is_readonly)

    def test_readonly_model_form(self):
        instance = ContentType.objects.get_for_model(ContentType)
        form = TestReadonlyModelForm(instance=instance)
        form.set_readonly(True)
        self.assertTrue(form.fields['app_label'].is_readonly)
        form.set_readonly(False)
        self.assertFalse(form.fields['app_label'].is_readonly)

    def test_whitespace_form(self):
        request = self.factory.post('/', {'first_name': ' John    ', 'last_name': '   '})
        form = TestWhitespaceForm(request.POST)
        self.assertFalse(form.is_valid())

        request = self.factory.post('/', {'first_name': ' Foo    ', 'last_name': '   Bar ack'})
        form = TestWhitespaceForm(request.POST)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['first_name'], 'Foo')
        self.assertEqual(form.cleaned_data['last_name'], 'Bar ack')

    def test_whitespace_model_form(self):
        instance = ContentType.objects.get_for_model(ContentType)
        form = TestWhitespaceModelForm(instance=instance, data={'name': ' content type ',
                                                                'app_label': ' contenttypes    ',
                                                                'model': '     '})
        self.assertFalse(form.is_valid())
        form = TestWhitespaceModelForm(instance=instance, data={'name': ' content type ',
                                                                'app_label': ' contenttypes    ',
                                                                'model': '   contenttype  '})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['app_label'], 'contenttypes')
        self.assertEqual(form.cleaned_data['model'], 'contenttype')

    def test_whitespace_request(self):
        instance = ContentType.objects.get_for_model(ContentType)
        request = self.factory.post('/', data={'name': ' content type ',
                                               'app_label': ' contenttypes    ',
                                               'model': '   contenttype  '})
        form = TestWhitespaceModelForm(request.POST, instance=instance)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['app_label'], 'contenttypes')
        self.assertEqual(form.cleaned_data['model'], 'contenttype')
