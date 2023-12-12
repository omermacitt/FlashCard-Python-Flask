from wtforms import Form, StringField, PasswordField, validators
from passlib.hash import sha256_crypt


def password_complexity_check(form, field):
    password = field.data
    if not any(char for char in password if char in "!@#$%^&*()_-+=<>?/"):
        raise validators.ValidationError("Parola en az bir özel karakter içermelidir.")
    
    if not any(char.isdigit( ) for char in password):
        raise validators.ValidationError("Parola en az bir rakam içermelidir.")


class RegisterForm(Form):
    name = StringField("İsim", validators=[validators.Length(max=25),
                                           validators.DataRequired(message="Lütfen bu alanı doldurunuz.")],
                       render_kw={
                           "placeholder": "İsim", "style": "width:420px;height:40px;margin-left:60px"
                       }
                       )
    
    surname = StringField("Soyisim", validators=[validators.Length(max=25),
                                                 validators.DataRequired(message="Lütfen bu alanı doldurunuz.")],
                          render_kw={
                              "placeholder": "Soyisim", "style": "width:420px;height:40px;margin-left:60px"
                          })
    nickname = StringField("Nickname", validators=[validators.DataRequired(message="Lütfen bu alanı doldurunuz.")],
                           render_kw={
                               "placeholder": "Nickname", "style": "width:420px;height:40px;margin-left:60px"
                           }
                           )
    password = PasswordField(label="Parola", validators=[validators.DataRequired("Lütfen parola alanını doldurunuz."),
                                                         password_complexity_check, validators.EqualTo(
            fieldname="confirm", message="Parolalar Uyuşmuyor")], render_kw={
        "placeholder": "Parola", "style": "width:420px;height:40px;margin-left:60px"
    })
    confirm = PasswordField(label="Doğrula", validators=[validators.DataRequired("Lütfen parola alanını doldurunuz.")],
                            render_kw={
                                "placeholder": "Doğrulama", "style": "width:420px;height:40px;margin-left:60px"
                            })


class LoginForm(Form):
    nickname = StringField("Nickname", validators=[validators.DataRequired(message="Lütfen bu alanı doldurunuz.")],
                           render_kw={
                               "placeholder": "Nickname", "style": "width:420px;height:40px;margin-left:60px"
                           })
    password = PasswordField("Parola", validators=[validators.DataRequired(message="Lütfen bu alanı doldurunuz.")],
                             render_kw={
                                 "placeholder": "Parola", "style": "width:420px;height:40px;margin-left:60px"
                             })

class InsertWord(Form):
    word = StringField("Word", validators=[validators.DataRequired(message="Lütfen bu alanı doldurunuz.")],
                       render_kw={"placeholder":"Kelime"})
    opposite = StringField("Opposite",validators=[validators.DataRequired(message="Lütfen bu alanı doldurunuz.")],
                           render_kw={"placeholder":"Karşılığı"})