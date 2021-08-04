import React, { HTMLAttributes } from 'react';
import styled, { css } from 'styled-components';

import Palette from '../../lib/css/Pallete';
import { TypoGraphyCategory, TypoGraphyTheme } from '../../lib/css/TempTypo';


type StyleParenProp = Pick<ParenProp, 'color' | 'size' | 'isInline'>;

export type ParenProp = {
  color?: Palette;
  size?: TypoGraphyCategory;
  children: React.ReactNode;
  id?: string;
  isInline?: boolean
} & React.HTMLAttributes<HTMLParagraphElement>

function P({
  color,
  size = TypoGraphyCategory.body,
  isInline = false,
  children,
  id,
  ...props
}: ParenProp) {
  return (
    <Paren  color={color} size={size} id={id} isInline={isInline} {...props}>
      {children}
    </Paren>
  );
}

const Paren = styled.p<StyleParenProp>`
  ${({ size }) => size && TypoGraphyTheme[size]}

  color: inherit;

  ${({ color }) => color && css`
    color: ${color};
  `}
  ${({isInline}) => isInline && css`
    display: inline-block;
  `}
`;

export default P;
