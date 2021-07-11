import { createGlobalStyle } from 'styled-components';
import reset from 'styled-reset';
import Typography from './Typography';

export const GlobalStyle = createGlobalStyle`
    ${reset}

    body {
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&family=Work+Sans:wght@400;500;700&display=swap');
        font-family: Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, 'Helvetica Neue', 'Segoe UI', 'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', sans-serif;

        margin:0;
        padding: 0;
        min-height: 100%;
    }
    #root {
        min-height: 100vh;
    }
    html {
        height: 100%;
    }
    div{
        box-sizing: border-box;
    }
    button {
        font-family: inherit;
    }

    a {
        text-decoration: none;
        color: inherit;
    }
    input,button, input:focus, textarea, textarea:focus {
        outline: none;
        
        border: none;
        box-sizing: border-box;
    }

    textarea::placeholder{
        ${Typography.body1}
    }
`;
