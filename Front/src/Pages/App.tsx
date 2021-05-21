import React, { FC } from 'react';
import { Route, Router, Switch } from 'react-router-dom';
import Header from '../Feature/Header/Header';

import SignIn from '../Feature/SignIn/SignIn';
import SignUp from '../Feature/SignUp/EmailSignUp/SignUp';
import MailVf from '../Feature/SignUp/MailVerification/MailVf';

import S from './App.styled';
import SignUpPage from './SignUpPage';
import Landing from '../Feature/Landing/Landing';
import MyPage from '../Feature/MyPage/MyPage';

function App() {
  return (
    <>
      <Header />
      <S.AppMainWrapper>
        <Switch>
          <Route path="/signup" component={SignUpPage} />
          <Route path="/login" exact component={SignIn} />
          <Route path="/mypage" exact component={MyPage} />
          <Route path="/" exact component={Landing} />
        </Switch>
      </S.AppMainWrapper>
    </>
  );
}

export default App;
